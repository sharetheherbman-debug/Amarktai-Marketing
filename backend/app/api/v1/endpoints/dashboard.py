"""
Dashboard Feature Endpoints

Provides backend support for all dashboard widgets:
- AI Insights Feed (analytics-driven insights)
- Smart Scheduler (audience heatmap + optimal times)
- Viral Prediction (content viral scoring)
- Performance Prediction (content performance forecasting)
- Content Calendar (scheduled / posted events)
- Competitor Intelligence (competitor analysis)

Designed and created by AmarktAI Marketing
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.content import Content, ContentStatus
from app.models.user import User
from app.models.analytics import Analytics

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ViralPredictRequest(BaseModel):
    caption: str = ""
    hashtags: list[str] = []
    platform: str = "instagram"
    media_urls: list[str] = []


class PerformancePredictRequest(BaseModel):
    caption: str = ""
    hashtags: list[str] = []
    platform: str = "instagram"
    media_urls: list[str] = []


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return high-level dashboard KPI stats."""
    posted_count = db.query(func.count(Content.id)).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.POSTED,
    ).scalar() or 0

    leads_captured = db.query(func.count(Analytics.id)).filter(
        Analytics.user_id == current_user.id,
    ).scalar() or 0

    engagement_rate_avg = db.query(
        func.avg(
            case(
                (
                    (Content.views > 0),
                    ((Content.likes + Content.comments + Content.shares) * 100.0) / Content.views,
                ),
                else_=0.0,
            )
        )
    ).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.POSTED,
    ).scalar() or 0.0

    tokens_used = db.query(
        func.coalesce(func.sum(Content.llm_tokens_used), 0)
    ).filter(
        Content.user_id == current_user.id,
    ).scalar() or 0

    return {
        "postsPublished": int(posted_count),
        "engagementRate": f"{float(engagement_rate_avg):.1f}%",
        "leadsCaptures": int(leads_captured),
        "tokensUsed": int(tokens_used),
    }


# ─── AI Insights Feed ────────────────────────────────────────────────────────

@router.get("/insights")
async def get_ai_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Generate AI-driven insights based on the user's analytics, content,
    and platform activity.  Returns actionable insights sorted by impact.
    """
    insights: list[dict[str, Any]] = []
    now = datetime.utcnow()

    # --- Pending content insight ---
    pending_count = db.query(func.count(Content.id)).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.PENDING,
    ).scalar() or 0

    if pending_count > 0:
        insights.append({
            "id": str(uuid.uuid4()),
            "type": "warning",
            "title": f"{pending_count} Content Items Awaiting Approval",
            "description": f"You have {pending_count} pending content items. Review and approve them to keep your posting schedule on track.",
            "action": "Review content",
            "impact": "high" if pending_count >= 5 else "medium",
            "timestamp": now.isoformat(),
            "read": False,
        })

    # --- Total posts insight ---
    total_posts = db.query(func.count(Content.id)).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.POSTED,
    ).scalar() or 0

    if total_posts > 0:
        insights.append({
            "id": str(uuid.uuid4()),
            "type": "achievement",
            "title": f"{total_posts} Posts Published",
            "description": f"You've published {total_posts} pieces of content. Keep up the great work!",
            "impact": "medium",
            "timestamp": now.isoformat(),
            "read": True,
        })

    # --- Scheduled posts insight ---
    upcoming = db.query(func.count(Content.id)).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.SCHEDULED,
        Content.scheduled_for >= now,
    ).scalar() or 0

    if upcoming > 0:
        insights.append({
            "id": str(uuid.uuid4()),
            "type": "tip",
            "title": f"{upcoming} Posts Scheduled",
            "description": f"You have {upcoming} posts queued for publishing. Your schedule is looking healthy.",
            "action": "View schedule",
            "impact": "low",
            "timestamp": now.isoformat(),
            "read": True,
        })

    # --- Platform engagement tip ---
    insights.append({
        "id": str(uuid.uuid4()),
        "type": "tip",
        "title": "Optimal Posting Window",
        "description": "Based on industry data, 6:00 PM – 8:00 PM is typically the best posting window for maximum engagement.",
        "action": "Schedule posts",
        "impact": "medium",
        "timestamp": now.isoformat(),
        "read": True,
    })

    # --- Trending opportunity ---
    insights.append({
        "id": str(uuid.uuid4()),
        "type": "opportunity",
        "title": "Video Content Performs 3× Better",
        "description": "Across all platforms, video content consistently outperforms images and text. Consider prioritising video in your content mix.",
        "action": "Create video",
        "impact": "high",
        "timestamp": now.isoformat(),
        "read": False,
    })

    # --- Engagement reminder ---
    insights.append({
        "id": str(uuid.uuid4()),
        "type": "trend",
        "title": "Reply Within 1 Hour",
        "description": "Replying to comments within the first hour can boost algorithmic distribution by up to 30% across most platforms.",
        "impact": "medium",
        "timestamp": now.isoformat(),
        "read": True,
    })

    return insights


# ─── Smart Scheduler – Audience Heatmap ──────────────────────────────────────

@router.get("/scheduler/heatmap")
async def get_scheduler_heatmap(
    platform: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Return a 24-hour audience activity heatmap with optimal posting slots.
    Uses the SmartScheduler service when historical data is available,
    otherwise returns platform-typical patterns.
    """
    from app.services.smart_scheduler import SmartScheduler

    scheduler = SmartScheduler()

    # Build time slots from the scheduler service
    time_slots = []
    optimal_times = scheduler.get_optimal_posting_times(
        platform if platform != "all" else "instagram"
    )

    # Build a full 24-hour map
    import math
    for hour in range(24):
        # Sine-wave model for typical audience activity:
        #   offset -6  → trough at 6 AM, peak at ~18:00 (6 PM)
        #   amplitude 35, midline 55 → range ≈ 20–90
        base = math.sin((hour - 6) * math.pi / 12) * 35 + 55
        score = max(20, min(95, round(base)))

        # Boost hours that the service recommends
        for slot in optimal_times:
            h, _ = map(int, slot.time.split(":"))
            if h == hour:
                score = max(score, round(slot.score * 100))

        time_slots.append({
            "hour": hour,
            "score": score,
            "audience_count": max(500, int(score * 50)),
            "engagement": round(score / 12, 1),
        })

    # Best 3 slots
    best = sorted(time_slots, key=lambda s: s["score"], reverse=True)[:3]

    return {
        "time_slots": time_slots,
        "best_slots": best,
        "platform": platform,
    }


@router.get("/scheduler/posts")
async def get_scheduled_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return upcoming scheduled posts."""
    posts = (
        db.query(Content)
        .filter(
            Content.user_id == current_user.id,
            Content.status.in_([
                ContentStatus.SCHEDULED,
                ContentStatus.APPROVED,
            ]),
        )
        .order_by(func.isnull(Content.scheduled_for).asc(), Content.scheduled_for.asc(), Content.created_at.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "id": p.id,
            "title": p.title or "Untitled",
            "platform": p.platform,
            "scheduled_time": (
                p.scheduled_for.isoformat() if p.scheduled_for else None
            ),
            "status": p.status,
            "predicted_engagement": 0,
            "optimal_score": 0,
        }
        for p in posts
    ]


# ─── Viral Prediction ────────────────────────────────────────────────────────

@router.post("/viral-predict")
async def predict_viral_potential(
    body: ViralPredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Analyse content for viral potential.  Uses the ContentPerformancePredictor
    service plus rule-based viral scoring.
    """
    from app.services.content_predictor import ContentPerformancePredictor

    predictor = ContentPerformancePredictor()

    content_data = {
        "caption": body.caption,
        "hashtags": body.hashtags,
        "media_urls": body.media_urls,
    }

    # Run the predictor for factor analysis
    prediction = predictor.predict_performance(content_data, body.platform)
    scores = predictor._analyze_content_factors(content_data, body.platform)

    # Compute viral sub-scores (0-100 scale).
    # caption_length is used as a proxy for emotional_impact because longer
    # captions with more narrative tend to carry stronger emotional hooks.
    hook_strength = round(scores.get("hook_strength", 0.6) * 100)
    emotional_impact = round(scores.get("caption_length", 0.6) * 100)
    shareability = round(scores.get("hashtag_count", 0.6) * 100)
    timing = round(scores.get("posting_time", 0.7) * 100)
    uniqueness = round(scores.get("platform_fit", 0.6) * 100)

    overall = round(
        hook_strength * 0.25
        + emotional_impact * 0.15
        + shareability * 0.20
        + timing * 0.15
        + uniqueness * 0.25
    )

    viral_probability = min(95, max(5, overall - 10))
    estimated_reach = int(viral_probability * 1800)

    # Build factor lists
    positive: list[str] = []
    negative: list[str] = []

    if hook_strength >= 70:
        positive.append("Strong opening hook detected")
    else:
        negative.append("Opening hook could be stronger")

    if shareability >= 70:
        positive.append("Good hashtag coverage for discoverability")
    else:
        negative.append("Hashtag count below recommended range")

    if len(body.media_urls) > 0:
        positive.append("Visual media included — boosts engagement")
    else:
        negative.append("No media attached — add visuals for 2× engagement")

    if timing >= 70:
        positive.append("Content fits platform format expectations")
    else:
        negative.append("Consider adjusting content for platform norms")

    if uniqueness >= 70:
        positive.append("Content aligns well with platform audience")

    time_to_viral = (
        "24-48 hours" if viral_probability >= 60
        else "3-5 days" if viral_probability >= 40
        else "7+ days"
    )

    return {
        "score": {
            "overall": overall,
            "hook_strength": hook_strength,
            "emotional_impact": emotional_impact,
            "shareability": shareability,
            "timing": timing,
            "uniqueness": uniqueness,
        },
        "viral_probability": viral_probability,
        "estimated_reach": estimated_reach,
        "time_to_viral": time_to_viral,
        "factors": {"positive": positive, "negative": negative},
        "recommendations": prediction.improvement_suggestions,
    }


# ─── Performance Prediction ──────────────────────────────────────────────────

@router.post("/performance-predict")
async def predict_performance(
    body: PerformancePredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Predict expected views, engagement and CTR for content before posting.
    """
    from app.services.content_predictor import ContentPerformancePredictor

    predictor = ContentPerformancePredictor()
    content_data = {
        "caption": body.caption,
        "hashtags": body.hashtags,
        "media_urls": body.media_urls,
    }

    # Pull historical averages for this user if available
    historical: dict[str, Any] = {}
    avg_row = (
        db.query(
            func.avg(Content.views).label("avg_views"),
            func.avg(Content.likes + Content.comments).label("avg_engagement"),
            func.avg(Content.ctr).label("avg_ctr"),
        )
        .filter(
            Content.user_id == current_user.id,
            Content.status == ContentStatus.POSTED,
        )
        .first()
    )
    if avg_row and avg_row.avg_views:
        historical = {
            "avg_views": float(avg_row.avg_views),
            "avg_engagement": float(avg_row.avg_engagement or 100),
            "avg_ctr": float(avg_row.avg_ctr or 5.0),
        }

    prediction = predictor.predict_performance(
        content_data, body.platform, historical or None
    )

    return {
        "predicted_views": prediction.predicted_views,
        "predicted_engagement": prediction.predicted_engagement,
        "predicted_ctr": prediction.predicted_ctr,
        "confidence_score": prediction.confidence_score,
        "risk_level": prediction.risk_level,
        "improvement_suggestions": prediction.improvement_suggestions,
    }


# ─── Content Calendar ────────────────────────────────────────────────────────

@router.get("/calendar")
async def get_calendar_events(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Return content events for the calendar view.
    Includes scheduled, posted, and approved content.
    Optional `month` param in YYYY-MM format.
    """
    query = db.query(Content).filter(
        Content.user_id == current_user.id,
        Content.status.in_([
            ContentStatus.SCHEDULED,
            ContentStatus.POSTED,
            ContentStatus.APPROVED,
            ContentStatus.PENDING,
        ]),
    )

    # Filter by month if provided
    if month:
        try:
            start = datetime.strptime(month, "%Y-%m")
            end = (start + timedelta(days=32)).replace(day=1)
            query = query.filter(
                Content.created_at >= start,
                Content.created_at < end,
            )
        except ValueError:
            pass

    items = query.order_by(Content.created_at.desc()).limit(200).all()

    events: list[dict[str, Any]] = []
    for c in items:
        event_date = c.scheduled_for or c.posted_at or c.created_at
        events.append({
            "id": c.id,
            "date": event_date.isoformat() if event_date else None,
            "platform": c.platform,
            "title": c.title or "Untitled",
            "status": c.status,
            "time": event_date.strftime("%I:%M %p") if event_date else "",
        })

    return events


# ─── Competitor Intelligence ─────────────────────────────────────────────────

@router.get("/competitors")
async def get_competitor_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Return competitor intelligence data.
    If the Competitor Shadow Analyzer tool has been run, returns stored data.
    Otherwise returns a meaningful "not configured" state.
    """
    from app.models.tools import CompetitorProfile

    profiles = (
        db.query(CompetitorProfile)
        .filter(CompetitorProfile.user_id == current_user.id)
        .order_by(CompetitorProfile.created_at.desc())
        .limit(10)
        .all()
    )

    competitors = []
    for p in profiles:
        competitors.append({
            "id": p.id,
            "name": p.competitor_name or "Unknown",
            "handle": p.competitor_url or "",
            "platform": p.platform or "unknown",
            "followers": 0,
            "engagement": 0,
            "posts_per_week": 0,
            "growth": 0,
            "strengths": p.strengths or [],
            "weaknesses": p.weaknesses or [],
            "top_content": p.content_types or [],
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {
        "competitors": competitors,
        "has_data": len(competitors) > 0,
        "message": (
            None if competitors
            else "No competitor data yet. Run the Competitor Shadow Analyzer tool to populate this."
        ),
    }


@router.get("/competitors/trends")
async def get_trending_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Return trending topics.  In production these come from external
    trend APIs (SerpAPI, Google Trends, NewsAPI).  When those keys are
    not configured, returns a "not configured" indicator.
    """
    from app.core.config import settings

    has_trend_key = bool(
        getattr(settings, "SERPAPI_KEY", None)
        or getattr(settings, "GOOGLE_TRENDS_API_KEY", None)
        or getattr(settings, "NEWSAPI_KEY", None)
    )

    if not has_trend_key:
        return [{
            "topic": "Trend data unavailable",
            "volume": 0,
            "growth": 0,
            "sentiment": "neutral",
            "related": [],
            "needs_api_key": True,
            "message": "Add a SerpAPI, Google Trends, or NewsAPI key in Integrations to enable live trending data.",
        }]

    # Placeholder for real trend integration
    return [{
        "topic": "Trends configured",
        "volume": 0,
        "growth": 0,
        "sentiment": "neutral",
        "related": [],
        "needs_api_key": False,
    }]
