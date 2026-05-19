from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.models.content import Content as ContentModel
from app.models.analytics import Analytics as AnalyticsModel
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary, PlatformStats, DailyStat
from app.api.deps import get_current_user

router = APIRouter()


class ManualMetricIn(BaseModel):
    content_id: str | None = None
    platform: str = "unknown"
    metric_date: date | None = None
    impressions: int = 0
    reach: int = 0
    clicks: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    conversions: int = 0


def _content_score(metrics: dict[str, int]) -> float:
    impressions = max(metrics.get("impressions", 0), 1)
    reach = max(metrics.get("reach", 0), 1)
    clicks = metrics.get("clicks", 0)
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    saves = metrics.get("saves", 0)
    conversions = metrics.get("conversions", 0)

    engagement_rate = (likes + comments + shares + saves) / impressions
    ctr = clicks / impressions
    conversion_rate = conversions / reach
    raw = (engagement_rate * 45) + (ctr * 35) + (conversion_rate * 20)
    return round(min(100.0, max(0.0, raw * 100)), 2)


@router.post("/manual-metrics")
async def upsert_manual_metrics(
    payload: ManualMetricIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metric_date = payload.metric_date or date.today()
    metrics = {
        "impressions": payload.impressions,
        "reach": payload.reach,
        "clicks": payload.clicks,
        "likes": payload.likes,
        "comments": payload.comments,
        "shares": payload.shares,
        "saves": payload.saves,
        "conversions": payload.conversions,
    }
    score = _content_score(metrics)

    row = (
        db.query(AnalyticsModel)
        .filter(
            AnalyticsModel.user_id == current_user.id,
            AnalyticsModel.content_id == payload.content_id,
            AnalyticsModel.platform == payload.platform,
            AnalyticsModel.date == metric_date,
        )
        .first()
    )
    if not row:
        row = AnalyticsModel(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            content_id=payload.content_id,
            platform=payload.platform,
            date=metric_date,
        )
        db.add(row)

    row.views = payload.impressions
    row.posts = 1
    row.likes = payload.likes
    row.comments = payload.comments
    row.shares = payload.shares
    row.clicks = payload.clicks
    row.ctr = round((payload.clicks / payload.impressions) * 100, 2) if payload.impressions > 0 else 0.0

    if payload.content_id:
        content = db.query(ContentModel).filter(ContentModel.id == payload.content_id, ContentModel.user_id == current_user.id).first()
        if content:
            content.views = payload.impressions
            content.likes = payload.likes
            content.comments = payload.comments
            content.shares = payload.shares
            content.clicks = payload.clicks
            content.ctr = row.ctr
            feedback = dict(content.performance_feedback or {})
            feedback.update(metrics)
            feedback["content_score"] = score
            feedback["metrics_source"] = "manual"
            content.performance_feedback = feedback

    db.commit()
    return {
        "ok": True,
        "content_score": score,
        "learning_active": True,
    }


@router.post("/import-csv")
async def import_metrics_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    content = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    required = {"platform", "impressions", "reach", "clicks", "likes", "comments", "shares", "saves", "conversions"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail=f"CSV must include columns: {sorted(required)}")

    imported = 0
    for record in reader:
        payload = ManualMetricIn(
            content_id=(record.get("content_id") or None),
            platform=(record.get("platform") or "unknown").strip().lower(),
            metric_date=date.fromisoformat(record["metric_date"]) if record.get("metric_date") else date.today(),
            impressions=int(record.get("impressions") or 0),
            reach=int(record.get("reach") or 0),
            clicks=int(record.get("clicks") or 0),
            likes=int(record.get("likes") or 0),
            comments=int(record.get("comments") or 0),
            shares=int(record.get("shares") or 0),
            saves=int(record.get("saves") or 0),
            conversions=int(record.get("conversions") or 0),
        )
        await upsert_manual_metrics(payload, db=db, current_user=current_user)
        imported += 1

    return {"ok": True, "imported": imported, "learning_active": imported > 0}


@router.get("/learning-status")
async def learning_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metrics_records = (
        db.query(func.count(AnalyticsModel.id))
        .filter(AnalyticsModel.user_id == current_user.id)
        .scalar()
        or 0
    )
    return {
        "learning_active": metrics_records > 0,
        "metrics_records": metrics_records,
        "message": "Learning active" if metrics_records > 0 else "Learning starts after metrics are captured or imported.",
    }


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics summary for the current user."""
    total_posts = db.query(ContentModel).filter(
        ContentModel.user_id == current_user.id,
        ContentModel.status == "posted"
    ).count()

    result = db.query(
        func.sum(ContentModel.views).label("total_views"),
        func.sum(ContentModel.likes + ContentModel.comments + ContentModel.shares).label("total_engagement"),
        func.avg(ContentModel.ctr).label("avg_ctr")
    ).filter(
        ContentModel.user_id == current_user.id,
        ContentModel.status == "posted"
    ).first()

    platform_stats = db.query(
        ContentModel.platform,
        func.count(ContentModel.id).label("posts"),
        func.sum(ContentModel.views).label("views"),
        func.sum(ContentModel.likes + ContentModel.comments + ContentModel.shares).label("engagement"),
        func.avg(ContentModel.ctr).label("ctr")
    ).filter(
        ContentModel.user_id == current_user.id,
        ContentModel.status == "posted"
    ).group_by(ContentModel.platform).all()

    platform_breakdown = {}
    for stat in platform_stats:
        platform_breakdown[stat.platform] = PlatformStats(
            posts=stat.posts or 0,
            views=stat.views or 0,
            engagement=stat.engagement or 0,
            ctr=round(stat.ctr or 0, 2)
        )

    daily_stats = []
    for i in range(7):
        day = datetime.now() - timedelta(days=i)
        day_content = db.query(ContentModel).filter(
            ContentModel.user_id == current_user.id,
            ContentModel.status == "posted",
            func.date(ContentModel.posted_at) == day.date()
        ).all()
        daily_stats.append(DailyStat(
            date=day.strftime("%Y-%m-%d"),
            posts=len(day_content),
            views=sum(c.views for c in day_content),
            engagement=sum(c.likes + c.comments + c.shares for c in day_content)
        ))
    daily_stats.reverse()

    metrics_records = (
        db.query(func.count(AnalyticsModel.id))
        .filter(AnalyticsModel.user_id == current_user.id)
        .scalar()
        or 0
    )

    return AnalyticsSummary(
        total_posts=total_posts,
        total_views=result.total_views or 0,
        total_engagement=result.total_engagement or 0,
        avg_ctr=round(result.avg_ctr or 0, 2),
        platform_breakdown=platform_breakdown,
        daily_stats=daily_stats,
        learning_active=metrics_records > 0,
        metrics_records=metrics_records,
    )


@router.get("/platform/{platform}", response_model=PlatformStats)
async def get_platform_analytics(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics for a specific platform."""
    result = db.query(
        func.count(ContentModel.id).label("posts"),
        func.sum(ContentModel.views).label("views"),
        func.sum(ContentModel.likes + ContentModel.comments + ContentModel.shares).label("engagement"),
        func.avg(ContentModel.ctr).label("ctr")
    ).filter(
        ContentModel.user_id == current_user.id,
        ContentModel.platform == platform,
        ContentModel.status == "posted"
    ).first()

    return PlatformStats(
        posts=result.posts or 0,
        views=result.views or 0,
        engagement=result.engagement or 0,
        ctr=round(result.ctr or 0, 2)
    )
