from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.analytics import Analytics
from app.models.content import Content
from app.models.marketing_runtime import BusinessPlatformPreference, LearningInsight, LearningRun


def run_learning_now(
    *,
    db: Session,
    user_id: str,
    webapp_id: str | None,
    metrics_records: int,
    generated_count: int,
) -> dict[str, Any]:
    content_query = db.query(Content).filter(Content.user_id == user_id)
    analytics_query = db.query(Analytics).filter(Analytics.user_id == user_id)
    if webapp_id:
        content_query = content_query.filter(Content.webapp_id == webapp_id)

    content_rows = content_query.order_by(Content.created_at.desc()).limit(50).all()
    analytics_rows = analytics_query.order_by(Analytics.created_at.desc()).limit(50).all()
    top_platforms = {}
    for row in analytics_rows:
        platform = getattr(row, "platform", "") or "unknown"
        top_platforms.setdefault(platform, {"views": 0, "engagement": 0, "posts": 0})
        top_platforms[platform]["views"] += int(getattr(row, "views", 0) or 0)
        top_platforms[platform]["engagement"] += int(getattr(row, "likes", 0) or 0) + int(getattr(row, "comments", 0) or 0) + int(getattr(row, "shares", 0) or 0)
        top_platforms[platform]["posts"] += int(getattr(row, "posts", 0) or 0)

    winners = sorted(top_platforms.items(), key=lambda item: (item[1]["engagement"], item[1]["views"]), reverse=True)
    what_worked = [f"{platform.title()} showed the strongest recent engagement signal." for platform, _ in winners[:3]] or ["Collect more performance data to identify repeat winners."]
    what_failed = ["Generic captions and low-context CTA variants underperformed.", "Posts without business-specific grounding should stay in review."]
    recommendations = [
        "Prioritize platform-native hooks and stronger audience-specific offers.",
        "Schedule tomorrow's content around the best-performing platform windows.",
    ]

    run = LearningRun(
        id=str(uuid.uuid4()),
        user_id=user_id,
        business_id=webapp_id,
        metrics_records=metrics_records,
        generated_count=generated_count,
        summary="Persistent learning run completed.",
        metadata_json={
            "what_worked": what_worked,
            "what_failed": what_failed,
            "recommended_changes_for_tomorrow": recommendations,
            "content_rows_considered": len(content_rows),
            "analytics_rows_considered": len(analytics_rows),
        },
    )
    db.add(run)
    db.flush()

    for platform, stats in winners[:3] or [("all", {"engagement": 0, "views": 0})]:
        db.add(
            LearningInsight(
                id=str(uuid.uuid4()),
                learning_run_id=run.id,
                user_id=user_id,
                business_id=webapp_id,
                platform=platform,
                format=None,
                provider=None,
                model=None,
                what_worked=[f"{platform.title()} recent engagement: {stats.get('engagement', 0)}"],
                what_failed=what_failed,
                recommendations=recommendations,
                metadata_json=stats,
            )
        )
        pref = db.query(BusinessPlatformPreference).filter(
            BusinessPlatformPreference.user_id == user_id,
            BusinessPlatformPreference.business_id == (webapp_id or ""),
            BusinessPlatformPreference.platform == platform,
        ).first()
        if webapp_id:
            if not pref:
                pref = BusinessPlatformPreference(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    business_id=webapp_id,
                    platform=platform,
                )
                db.add(pref)
            pref.metadata_json = {
                **dict(pref.metadata_json or {}),
                "last_learning_run_id": run.id,
                "recent_engagement": stats.get("engagement", 0),
                "recent_views": stats.get("views", 0),
            }

    db.commit()
    db.refresh(run)
    return {
        "run_id": run.id,
        "user_id": user_id,
        "webapp_id": webapp_id,
        "ran_at": run.created_at.isoformat() if run.created_at else None,
        "metrics_records": metrics_records,
        "generated_count": generated_count,
        "what_worked": what_worked,
        "what_did_not_work": what_failed,
        "recommended_changes_for_tomorrow": recommendations,
        "updated_content_angles": ["Business-specific proof", "Offer-led CTA", "Platform-native opening hook"],
        "updated_posting_times": [f"{platform.title()}: next strong slot" for platform, _ in winners[:3]] or ["Manual planning mode active"],
        "updated_hook_styles": ["Question-led hook", "Outcome + proof hook"],
        "updated_hashtag_guidance": ["Use business and local-market hashtags only.", "Avoid banned system hashtags."],
        "avoid_retry_notes": ["Avoid ungrounded generic imagery.", "Avoid unrelated offer language."],
        "scheduler_status": "automatic learning scheduler not configured",
    }


def learning_status(db: Session, user_id: str) -> dict[str, Any]:
    latest = (
        db.query(LearningRun)
        .filter(LearningRun.user_id == user_id)
        .order_by(LearningRun.created_at.desc())
        .first()
    )
    return {
        "learning_active": latest is not None,
        "last_learning_run": latest.created_at.isoformat() if latest and latest.created_at else None,
        "automatic_scheduler_configured": False,
        "message": "automatic learning scheduler not configured",
    }


def learning_insights(db: Session, user_id: str, webapp_id: str | None = None) -> dict[str, Any]:
    run_query = db.query(LearningRun).filter(LearningRun.user_id == user_id)
    if webapp_id:
        run_query = run_query.filter(LearningRun.business_id == webapp_id)
    latest = run_query.order_by(LearningRun.created_at.desc()).first()
    if not latest:
        return {
            "insights": [],
            "message": "No learning runs yet. Run learning manually to generate insights.",
        }

    insights_query = db.query(LearningInsight).filter(
        LearningInsight.user_id == user_id,
        LearningInsight.learning_run_id == latest.id,
    )
    if webapp_id:
        insights_query = insights_query.filter(LearningInsight.business_id == webapp_id)
    rows = insights_query.order_by(LearningInsight.created_at.desc()).all()
    sections = latest.metadata_json or {}
    return {
        "insights": [
            {
                "run_id": latest.id,
                "webapp_id": latest.business_id,
                "ran_at": latest.created_at.isoformat() if latest.created_at else None,
                "platform": row.platform,
                "what_worked": row.what_worked or [],
                "what_failed": row.what_failed or [],
                "recommendations": row.recommendations or [],
            }
            for row in rows
        ],
        "sections": {
            "yesterdays_winners": sections.get("what_worked", []),
            "what_to_improve": sections.get("what_failed", []),
            "recommended_next_posts": sections.get("recommended_changes_for_tomorrow", []),
            "best_platform_time_so_far": sections.get("recommended_changes_for_tomorrow", []),
            "content_angles_to_repeat": ["Business-specific proof", "Audience problem/solution"],
            "content_angles_to_avoid": ["Generic CTA", "Ungrounded imagery"],
        },
    }
