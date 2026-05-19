"""
Autonomous Posting & Self-Optimization Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.config import settings
from app.models.content import Content, ContentStatus
from app.models.user import User
from app.models.webapp import WebApp

router = APIRouter()

class BatchApproveRequest(BaseModel):
    content_ids: List[str]
    schedule_immediately: bool = True

class PostContentRequest(BaseModel):
    content_id: str
    scheduled_time: Optional[datetime] = None


class CampaignPlanRequest(BaseModel):
    webapp_id: str
    goals: list[str] = []
    platforms: list[str] = ["facebook", "instagram", "linkedin", "twitter", "tiktok", "youtube", "reddit"]


@router.post("/campaign-plan")
async def generate_campaign_plan(
    payload: CampaignPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webapp = db.query(WebApp).filter(
        WebApp.id == payload.webapp_id,
        WebApp.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    audience = webapp.target_audience or "general audience"
    product = webapp.name
    category = webapp.category or "general"
    goals = payload.goals or ["awareness", "engagement", "traffic"]
    platforms = payload.platforms
    cadence = "3-5 posts/week"
    best_times = {
        "facebook": "Wed 15:00",
        "instagram": "Wed 19:00",
        "linkedin": "Tue 09:00",
        "twitter": "Wed 12:00",
        "tiktok": "Thu 20:00",
        "youtube": "Fri 19:00",
        "reddit": "Wed 21:00",
    }
    compliance_warnings = [
        "Do not post regulated claims without human review.",
        "Avoid duplicate/spam posting patterns.",
        "Follow each platform terms and disclosure requirements.",
    ]
    return {
        "webapp_id": webapp.id,
        "audience": audience,
        "product_service": product,
        "goals": goals,
        "platforms": platforms,
        "content_pillars": [
            f"{category} education",
            "customer outcomes",
            "behind-the-scenes",
            "offer and CTA",
        ],
        "posting_cadence": cadence,
        "best_time_recommendations": {p: best_times.get(p, "Wed 12:00") for p in platforms},
        "compliance_warnings": compliance_warnings,
    }

@router.post("/batch-approve")
async def batch_approve_content(
    request: BatchApproveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve multiple content items in batch."""
    
    content_items = db.query(Content).filter(
        Content.id.in_(request.content_ids),
        Content.user_id == current_user.id,
        Content.status == ContentStatus.PENDING
    ).all()
    
    approved_count = 0
    for content in content_items:
        content.status = ContentStatus.APPROVED
        approved_count += 1
        
        # Schedule for posting if requested
        if request.schedule_immediately:
            # Get optimal posting time
            from app.agents.research_agent_v2 import ResearchAgentV2
            agent = ResearchAgentV2()
            optimal_time = await agent.get_optimal_posting_time(content.platform, current_user.timezone)
            
            # Parse time and set scheduled_for
            from datetime import datetime, timedelta
            now = datetime.now()
            hour, minute = map(int, optimal_time.replace(" AM", "").replace(" PM", "").split(":"))
            
            scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled < now:
                scheduled += timedelta(days=1)
            
            content.scheduled_for = scheduled
            content.status = ContentStatus.SCHEDULED
    
    db.commit()
    
    # Trigger posting worker
    if request.schedule_immediately:
        background_tasks.add_task(schedule_posts_worker, current_user.id)
    
    return {
        "message": f"Approved {approved_count} content items",
        "approved_ids": [c.id for c in content_items],
        "scheduled": request.schedule_immediately
    }

@router.post("/post/{content_id}")
async def post_content(
    content_id: str,
    request: PostContentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post content to platform immediately or schedule."""
    
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.status not in [ContentStatus.APPROVED, ContentStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"Content cannot be posted (status: {content.status})")
    
    if request.scheduled_time:
        content.scheduled_for = request.scheduled_time
        content.status = ContentStatus.SCHEDULED
        db.commit()
        
        return {
            "message": "Content scheduled",
            "content_id": content_id,
            "scheduled_for": request.scheduled_time
        }
    else:
        # Immediate posting is gated behind the ENABLE_AUTO_POST feature flag.
        if not settings.ENABLE_AUTO_POST:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Autonomous posting is currently disabled. "
                    "Set ENABLE_AUTO_POST=true in your environment to allow immediate publishing, "
                    "or schedule this content for a future time instead."
                ),
            )
        # Post immediately
        background_tasks.add_task(post_to_platform_worker, content_id, current_user.id)
        
        return {
            "message": "Content queued for posting",
            "content_id": content_id
        }

@router.get("/queue-status")
async def get_queue_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get status of content queue."""
    
    from sqlalchemy import func
    
    # Count by status
    status_counts = db.query(
        Content.status,
        func.count(Content.id).label("count")
    ).filter(
        Content.user_id == current_user.id
    ).group_by(Content.status).all()
    
    # Get upcoming scheduled posts
    upcoming = db.query(Content).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.SCHEDULED,
        Content.scheduled_for >= datetime.now()
    ).order_by(Content.scheduled_for).limit(10).all()
    
    return {
        "counts": {s.status: s.count for s in status_counts},
        "upcoming_posts": [
            {
                "id": c.id,
                "title": c.title,
                "platform": c.platform,
                "scheduled_for": c.scheduled_for
            }
            for c in upcoming
        ]
    }

@router.post("/sync-analytics")
async def sync_analytics(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync analytics from all connected platforms."""
    
    background_tasks.add_task(sync_analytics_worker, current_user.id)
    
    return {"message": "Analytics sync started"}

@router.get("/best-posting-times")
async def get_best_posting_times(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get optimal posting times based on historical performance."""
    
    from app.models.analytics import Analytics
    from sqlalchemy import func, extract
    
    # Get analytics data
    analytics = db.query(Analytics).filter(
        Analytics.user_id == current_user.id
    ).all()
    
    # Analyze by hour
    hourly_performance = {}
    for a in analytics:
        hour = a.date.hour if hasattr(a.date, 'hour') else 12
        if hour not in hourly_performance:
            hourly_performance[hour] = {"views": 0, "engagement": 0, "count": 0}
        hourly_performance[hour]["views"] += a.views
        hourly_performance[hour]["engagement"] += a.engagement
        hourly_performance[hour]["count"] += 1
    
    # Calculate averages and find best times
    best_times = []
    for hour, data in hourly_performance.items():
        if data["count"] > 0:
            avg_engagement = data["engagement"] / data["count"]
            best_times.append({
                "hour": hour,
                "avg_engagement": round(avg_engagement, 2),
                "total_views": data["views"]
            })
    
    best_times.sort(key=lambda x: x["avg_engagement"], reverse=True)
    
    return {
        "best_times": best_times[:5],
        "recommendation": f"Post between {best_times[0]['hour']}:00-{best_times[0]['hour']+2}:00 for highest engagement" if best_times else "Insufficient data"
    }

@router.get("/morning-digest")
async def morning_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the daily morning approval digest — all pending content ready for the
    user's morning review-and-approve workflow.

    The response includes:
    - ``pending_count``: total items awaiting approval.
    - ``pending_items``: list of content summaries (id, title, platform, created_at).
    - ``auto_post_enabled``: whether autonomous publishing is active.
    - ``scheduled_today``: count of posts already scheduled for today.
    """
    from datetime import date

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    pending = db.query(Content).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.PENDING,
    ).order_by(Content.created_at.desc()).all()

    scheduled_today = db.query(Content).filter(
        Content.user_id == current_user.id,
        Content.status == ContentStatus.SCHEDULED,
        Content.scheduled_for >= today_start,
        Content.scheduled_for <= today_end,
    ).count()

    return {
        "pending_count": len(pending),
        "pending_items": [
            {
                "id": c.id,
                "title": c.title,
                "platform": c.platform,
                "created_at": c.created_at,
            }
            for c in pending
        ],
        "auto_post_enabled": settings.ENABLE_AUTO_POST,
        "scheduled_today": scheduled_today,
        "message": (
            f"{len(pending)} item(s) ready for your approval. "
            "Review and approve to schedule or publish."
            if pending
            else "No pending content — you're all caught up!"
        ),
    }



async def schedule_posts_worker(user_id: str):
    """Worker to schedule approved posts."""
    from app.db.session import SessionLocal
    from app.workers.celery_app import celery_app
    
    db = SessionLocal()
    try:
        # Get all scheduled posts that need to be queued
        scheduled = db.query(Content).filter(
            Content.user_id == user_id,
            Content.status == ContentStatus.SCHEDULED,
            Content.scheduled_for <= datetime.now()
        ).all()
        
        for content in scheduled:
            # Queue for posting
            celery_app.send_task(
                "app.workers.tasks.post_content_to_platform",
                args=[content.id, user_id]
            )
            
    finally:
        db.close()

async def post_to_platform_worker(content_id: str, user_id: str):
    """Worker to post content to platform."""
    from app.workers.celery_app import celery_app
    
    celery_app.send_task(
        "app.workers.tasks.post_content_to_platform",
        args=[content_id, user_id]
    )

async def sync_analytics_worker(user_id: str):
    """Worker to sync analytics from platforms."""
    from app.workers.celery_app import celery_app
    
    celery_app.send_task(
        "app.workers.tasks.sync_platform_analytics",
        args=[user_id]
    )
