from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid

from app.db.base import get_db
from app.models.platform_connection import PlatformConnection as PlatformModel, PlatformType
from app.models.user import User
from app.schemas.platform import PlatformConnection, PlatformConnectionCreate
from app.api.deps import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Platform-specific algorithm insights (AI knowledge base)
# ---------------------------------------------------------------------------

_PLATFORM_ALGORITHM_INSIGHTS: dict[str, dict[str, Any]] = {
    "instagram": {
        "best_post_times": ["9:00 AM", "11:00 AM", "2:00 PM", "7:00 PM"],
        "content_priority": ["Reels", "Carousels", "Stories", "Static Posts"],
        "algorithm_tips": [
            "Reels get 3x more reach than static posts",
            "Post within the first 30 min of peak hours for maximum algorithmic boost",
            "Use 3-5 niche hashtags (avoid over-saturated ones)",
            "Engage back within the first hour to signal activity to the algorithm",
            "Story polls and questions boost engagement signals",
        ],
        "engagement_benchmarks": {"good_rate": 1.5, "great_rate": 3.5, "unit": "%"},
        "paid_ad_tips": [
            "Lookalike audiences (1-3%) from your email list outperform broad targeting",
            "Advantage+ Shopping Campaigns auto-optimize creative",
        ],
    },
    "facebook": {
        "best_post_times": ["1:00 PM", "3:00 PM", "8:00 PM"],
        "content_priority": ["Reels/Videos", "Link Posts", "Photos", "Text"],
        "algorithm_tips": [
            "Video content gets 6x more engagement than photo posts",
            "Groups dramatically outreach regular page posts",
            "Business pages: create up to 200 pages per personal account",
            "Facebook Ads Manager supports CBO for best ROI",
            "Live videos get 6x more interaction than regular video",
        ],
        "engagement_benchmarks": {"good_rate": 0.5, "great_rate": 1.5, "unit": "%"},
        "paid_ad_tips": [
            "Broad audiences often beat narrow targeting for retargeting",
            "Advantage+ audiences auto-expand targeting for lower CPM",
        ],
        "business_pages": {
            "max_pages_per_account": 200,
            "can_create": True,
            "setup_steps": [
                "Go to facebook.com/pages/create",
                "Choose Page type (Business or Brand)",
                "Set Page name, category and description",
                "Upload profile and cover photos",
                "Add call-to-action button",
            ],
        },
    },
    "youtube": {
        "best_post_times": ["12:00 PM", "3:00 PM", "7:00 PM"],
        "content_priority": ["Shorts", "Long-form (8-15 min)", "Live Streams"],
        "algorithm_tips": [
            "Shorts get 30x more impressions during discovery phase",
            "CTR > 6% triggers strong algorithmic distribution",
            "Watch time (first 48 hours) is the #1 ranking signal",
            "Custom thumbnails improve CTR by up to 30%",
            "Chapters in long videos increase average view duration",
        ],
        "engagement_benchmarks": {"good_rate": 2.0, "great_rate": 5.0, "unit": "%"},
        "paid_ad_tips": [
            "TrueView in-stream ads: skip after 5s - only pay when user watches 30s+",
            "Bumper ads (6s) are ideal for brand awareness at low CPM",
        ],
    },
    "tiktok": {
        "best_post_times": ["7:00 AM", "12:00 PM", "7:00 PM", "10:00 PM"],
        "content_priority": ["Vertical Short Videos (15-60s)", "Trending Sounds", "Duets/Stitches"],
        "algorithm_tips": [
            "First 3 seconds determine whether viewers keep watching - hook immediately",
            "Trending audio boosts reach by up to 50%",
            "Reply to comments with videos for extra reach",
            "Posting 3-5x per day dramatically increases algorithmic exposure",
            "Use 3-5 relevant hashtags - avoid #fyp alone",
        ],
        "engagement_benchmarks": {"good_rate": 5.0, "great_rate": 18.0, "unit": "%"},
        "paid_ad_tips": [
            "TopView Ads (first ad seen when opening app) get highest CTR",
            "Spark Ads boost existing organic content - lower CPM than new creative",
        ],
    },
    "twitter": {
        "best_post_times": ["8:00 AM", "12:00 PM", "5:00 PM", "9:00 PM"],
        "content_priority": ["Threads", "Polls", "Short Videos", "Images"],
        "algorithm_tips": [
            "Threads get 4x more engagement than single tweets",
            "Polls drive 300% more engagement than average tweets",
            "Tweet at the start of trending conversations for maximum reach",
            "Reply to large accounts in your niche for organic visibility",
            "Media tweets get 3x more engagement than text-only",
        ],
        "engagement_benchmarks": {"good_rate": 0.5, "great_rate": 2.0, "unit": "%"},
        "paid_ad_tips": [
            "Promoted Tweets with video get lowest CPC",
            "Follower campaigns target users similar to your followers",
        ],
    },
    "linkedin": {
        "best_post_times": ["8:00 AM", "12:00 PM", "5:00 PM"],
        "content_priority": ["Documents/Carousels", "Text Posts", "Videos", "Newsletters"],
        "algorithm_tips": [
            "Posts with 'documents' (multi-page PDFs) reach 3x further",
            "Early engagement (first 2 hours) determines organic reach",
            "Tag maximum 3 people - more tags reduce reach",
            "Company pages: post 2-5x per week for optimal reach",
            "Newsletter articles rank on Google - great for SEO",
        ],
        "engagement_benchmarks": {"good_rate": 2.0, "great_rate": 6.0, "unit": "%"},
        "paid_ad_tips": [
            "Lead Gen Forms convert 3x better than landing page ads",
            "Matched Audiences (upload customer email list) for retargeting",
        ],
        "business_pages": {
            "max_pages_per_account": 25,
            "can_create": True,
            "setup_steps": [
                "Click 'For Business' then 'Create a Company Page'",
                "Choose page type (Company, Showcase Page, or Educational)",
                "Fill in company details, industry, and logo",
                "Invite existing connections to follow the page",
            ],
        },
    },
    "pinterest": {
        "best_post_times": ["8:00 PM", "9:00 PM", "2:00 AM"],
        "content_priority": ["Idea Pins (video)", "Standard Pins", "Shopping Pins"],
        "algorithm_tips": [
            "Vertical images (2:3 ratio) get up to 60% more repins",
            "Pin descriptions with 200-300 words rank better in search",
            "Idea Pins (story-style) get maximum algorithmic push",
            "Seasonal content performs 30-45 days before the holiday",
            "Consistent daily pinning outperforms bulk scheduling",
        ],
        "engagement_benchmarks": {"good_rate": 0.3, "great_rate": 1.0, "unit": "%"},
        "paid_ad_tips": [
            "Shopping Ads convert 3x better than standard promoted pins",
            "Max Width Video Ads take up full feed width",
        ],
    },
    "reddit": {
        "best_post_times": ["9:00 AM", "12:00 PM", "6:00 PM"],
        "content_priority": ["Text Posts with Discussion", "Links", "Images/Infographics"],
        "algorithm_tips": [
            "Value-first posts (not promotional) earn trust before pitching",
            "Comment karma in a subreddit before posting content",
            "Ask Me Anything (AMA) posts drive massive engagement",
            "Cross-posting to 3-5 relevant subreddits increases reach",
            "Flairs improve discoverability within subreddits",
        ],
        "engagement_benchmarks": {"good_rate": 1.0, "great_rate": 5.0, "unit": "% upvote ratio"},
        "paid_ad_tips": [
            "Conversation Placement Ads appear inside post threads",
            "Interest & Community targeting with keyword targeting",
        ],
    },
    "bluesky": {
        "best_post_times": ["8:00 AM", "12:00 PM", "6:00 PM"],
        "content_priority": ["Text Posts", "Images", "Thread Posts"],
        "algorithm_tips": [
            "Bluesky uses open algorithms - you can choose your own feed algorithm",
            "Engage with Starter Packs to grow followers quickly",
            "Cross-post content from Twitter/X - many users are migrating",
            "Feeds (custom algorithms) provide niche reach without hashtags",
        ],
        "engagement_benchmarks": {"good_rate": 2.0, "great_rate": 8.0, "unit": "%"},
        "paid_ad_tips": [],
    },
    "threads": {
        "best_post_times": ["9:00 AM", "1:00 PM", "7:00 PM"],
        "content_priority": ["Short Text Posts", "Polls", "Images"],
        "algorithm_tips": [
            "Threads is still growing - early presence gives competitive advantage",
            "Cross-post Instagram Reels to Threads for doubled exposure",
            "Conversations and replies get priority in the feed algorithm",
            "Post during peak Instagram hours for cross-platform visibility",
        ],
        "engagement_benchmarks": {"good_rate": 3.0, "great_rate": 10.0, "unit": "%"},
        "paid_ad_tips": [],
    },
    "telegram": {
        "best_post_times": ["10:00 AM", "2:00 PM", "8:00 PM"],
        "content_priority": ["Rich Media Posts", "Polls", "Documents", "Voice Notes"],
        "algorithm_tips": [
            "Channels have no algorithm - post quality and frequency drive growth",
            "Polls get 5x more interaction than plain text",
            "Bot integrations can automate announcements and lead capture",
            "Cross-promote with other Telegram channels in your niche",
        ],
        "engagement_benchmarks": {"good_rate": 10.0, "great_rate": 25.0, "unit": "% view rate"},
        "paid_ad_tips": [],
    },
    "snapchat": {
        "best_post_times": ["10:00 PM", "11:00 PM"],
        "content_priority": ["Stories", "Spotlight (short videos)", "Snaps"],
        "algorithm_tips": [
            "Spotlight pays creators for viral content - target trending topics",
            "Story content with polls/questions gets replays",
            "Geofilters and branded lenses drive location-based awareness",
            "Post consistently: Snapchat rewards accounts that streak",
        ],
        "engagement_benchmarks": {"good_rate": 5.0, "great_rate": 15.0, "unit": "% view rate"},
        "paid_ad_tips": [
            "Collection Ads are ideal for e-commerce product discovery",
            "Dynamic Ads auto-generate from product catalogue",
        ],
    },
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlatformBudgetUpdate(BaseModel):
    monthly_ad_budget: Optional[float] = None
    daily_ad_budget: Optional[float] = None
    ad_budget_currency: Optional[str] = None
    ad_account_id: Optional[str] = None
    auto_post_enabled: Optional[bool] = None
    auto_reply_enabled: Optional[bool] = None
    posting_schedule: Optional[dict] = None


class BusinessPageCreate(BaseModel):
    page_name: str
    category: str
    description: Optional[str] = None
    website_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[PlatformConnection])
async def get_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all connected platforms for the current user."""
    platforms = db.query(PlatformModel).filter(
        PlatformModel.user_id == current_user.id,
        PlatformModel.is_active == True
    ).all()
    return platforms


@router.get("/{platform}/audit")
async def audit_platform_account(
    platform: PlatformType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Return an AI audit of the connected account including platform algorithm
    insights, best posting times, engagement benchmarks, and recommendations.
    """
    connection = db.query(PlatformModel).filter(
        PlatformModel.user_id == current_user.id,
        PlatformModel.platform == platform,
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Platform not connected")

    insights = _PLATFORM_ALGORITHM_INSIGHTS.get(platform.value, {})

    connected_at = connection.connected_at
    account_age_days = (datetime.utcnow() - connected_at.replace(tzinfo=None)).days if connected_at else 0
    is_new_account = account_age_days < 30

    return {
        "platform": platform.value,
        "account_name": connection.account_name,
        "account_id": connection.account_id,
        "connected_at": connected_at.isoformat() if connected_at else None,
        "account_age_days": account_age_days,
        "account_type": "new" if is_new_account else "established",
        "account_type_label": (
            "New Account - focus on consistency and engagement to build authority"
            if is_new_account
            else "Established Account - optimise for reach and conversion"
        ),
        "algorithm_insights": insights,
        "recommendations": _get_account_recommendations(platform.value, is_new_account),
        "can_create_business_pages": insights.get("business_pages", {}).get("can_create", False),
        "business_page_info": insights.get("business_pages"),
        "auto_post_enabled": connection.auto_post_enabled,
        "auto_reply_enabled": connection.auto_reply_enabled,
        "monthly_ad_budget": float(connection.monthly_ad_budget or 0),
    }


def _get_account_recommendations(platform: str, is_new: bool) -> list[str]:
    base = _PLATFORM_ALGORITHM_INSIGHTS.get(platform, {})
    recs = []
    if is_new:
        recs.append("Post 2-3x per day for the first 30 days to establish algorithmic presence")
        recs.append("Engage actively with similar content to signal niche relevance")
        recs.append("Do NOT use banned or over-saturated hashtags - use niche-specific ones")
    else:
        recs.append("Analyse top-performing posts and replicate their format")
        recs.append("A/B test captions and posting times to optimise CTR")

    times = base.get("best_post_times", [])
    if times:
        recs.append(f"Optimal posting windows: {', '.join(times[:3])}")

    tips = base.get("algorithm_tips", [])
    recs.extend(tips[:3])
    return recs


@router.get("/{platform}", response_model=PlatformConnection)
async def get_platform(
    platform: PlatformType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific platform connection."""
    connection = db.query(PlatformModel).filter(
        PlatformModel.user_id == current_user.id,
        PlatformModel.platform == platform
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Platform not connected")
    return connection


@router.post("/{platform}/connect", response_model=PlatformConnection)
async def connect_platform(
    platform: PlatformType,
    account_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manual platform connection is intentionally blocked; use OAuth integrations."""
    raise HTTPException(
        status_code=409,
        detail=(
            f"{platform.value} requires a real OAuth/platform connection. "
            "Use /api/v1/integrations/platforms/{platform}/connect instead."
        ),
    )


@router.post("/{platform}/create-business-page")
async def create_business_page(
    platform: PlatformType,
    body: BusinessPageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Business page creation is not implemented against live platform APIs."""
    raise HTTPException(
        status_code=501,
        detail=(
            f"{platform.value} business page creation is not supported yet. "
            "Create the page directly in the platform and then connect it with OAuth."
        ),
    )


@router.patch("/{platform}/budget")
async def update_platform_budget(
    platform: PlatformType,
    body: PlatformBudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update per-platform ad budget, auto-post/reply flags, and posting schedule."""
    connection = db.query(PlatformModel).filter(
        PlatformModel.user_id == current_user.id,
        PlatformModel.platform == platform,
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Platform not connected")

    if body.monthly_ad_budget is not None:
        connection.monthly_ad_budget = body.monthly_ad_budget
    if body.daily_ad_budget is not None:
        connection.daily_ad_budget = body.daily_ad_budget
    if body.ad_budget_currency is not None:
        connection.ad_budget_currency = body.ad_budget_currency
    if body.ad_account_id is not None:
        connection.ad_account_id = body.ad_account_id
    if body.auto_post_enabled is not None:
        connection.auto_post_enabled = body.auto_post_enabled
    if body.auto_reply_enabled is not None:
        connection.auto_reply_enabled = body.auto_reply_enabled
    if body.posting_schedule is not None:
        connection.posting_schedule = body.posting_schedule

    db.commit()
    db.refresh(connection)
    return {
        "platform": platform,
        "monthly_ad_budget": float(connection.monthly_ad_budget or 0),
        "daily_ad_budget": float(connection.daily_ad_budget or 0),
        "ad_budget_currency": connection.ad_budget_currency,
        "ad_account_id": connection.ad_account_id,
        "auto_post_enabled": connection.auto_post_enabled,
        "auto_reply_enabled": connection.auto_reply_enabled,
        "posting_schedule": connection.posting_schedule,
    }


@router.post("/{platform}/disconnect")
async def disconnect_platform(
    platform: PlatformType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect a platform."""
    connection = db.query(PlatformModel).filter(
        PlatformModel.user_id == current_user.id,
        PlatformModel.platform == platform
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Platform not connected")

    connection.is_active = False
    db.commit()
    return {"message": f"Disconnected from {platform}"}
