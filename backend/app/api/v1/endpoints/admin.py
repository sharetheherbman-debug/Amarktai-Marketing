"""
Admin Endpoints — system-wide configuration managed by the admin.

Allows the site administrator to:
- Set system-level API keys (HuggingFace, social platform credentials)
- Toggle feature flags
- View system health & user stats
- Trigger manual content generation runs

All endpoints require admin access (see app.api.deps.get_admin_user).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.core.config import settings
from app.models.content import Content, ContentStatus
from app.models.user import User
from app.models.webapp import WebApp

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SystemKeyUpdate(BaseModel):
    key_name: str
    key_value: str


class FeatureFlagUpdate(BaseModel):
    enable_auto_post: bool | None = None
    enable_auto_reply: bool | None = None
    enable_ab_testing: bool | None = None
    enable_viral_prediction: bool | None = None
    enable_cost_tracking: bool | None = None
    max_content_per_day: int | None = None
    max_engagement_replies_per_day: int | None = None


class TriggerGenerationRequest(BaseModel):
    user_id: str | None = None  # None = all users
    window: str = "manual"


# ---------------------------------------------------------------------------
# System health & stats
# ---------------------------------------------------------------------------

@router.get("/health")
async def admin_health(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Return system health metrics."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_webapps = db.query(func.count(WebApp.id)).scalar() or 0
    total_content = db.query(func.count(Content.id)).scalar() or 0
    pending_content = (
        db.query(func.count(Content.id))
        .filter(Content.status == ContentStatus.PENDING)
        .scalar()
        or 0
    )
    posted_content = (
        db.query(func.count(Content.id))
        .filter(Content.status == ContentStatus.POSTED)
        .scalar()
        or 0
    )

    # Check configured system keys
    configured_keys: list[str] = []
    key_names = [
        "GENX_API_KEY",
        "QWEN_API_KEY",
        "HUGGINGFACE_TOKEN",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "FIRECRAWL_API_KEY",
        "TWITTER_API_KEY",
        "META_APP_ID",
        "LINKEDIN_CLIENT_ID",
        "TIKTOK_CLIENT_KEY",
        "YOUTUBE_CLIENT_ID",
    ]
    for k in key_names:
        if getattr(settings, k, ""):
            configured_keys.append(k)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "total_users": total_users,
            "total_webapps": total_webapps,
            "total_content": total_content,
            "pending_content": pending_content,
            "posted_content": posted_content,
        },
        "configured_system_keys": configured_keys,
        "feature_flags": {
            "enable_auto_post": settings.ENABLE_AUTO_POST,
            "enable_auto_reply": settings.ENABLE_AUTO_REPLY,
            "enable_ab_testing": settings.ENABLE_AB_TESTING,
            "enable_viral_prediction": settings.ENABLE_VIRAL_PREDICTION,
            "enable_cost_tracking": settings.ENABLE_COST_TRACKING,
            "max_content_per_day": settings.MAX_CONTENT_PER_DAY,
        },
    }


# ---------------------------------------------------------------------------
# System API key management
# ---------------------------------------------------------------------------

_ALLOWED_SYSTEM_KEYS = {
    "HUGGINGFACE_TOKEN",
    "GENX_API_KEY",
    "GENX_BASE_URL",
    "GENX_DEFAULT_MODEL",
    "GENX_TIMEOUT",
    "GENX_MODEL_ALLOWLIST",
    "GENX_MODEL_FALLBACKS",
    "GENX_MODEL_COPY",
    "GENX_MODEL_STRATEGY",
    "GENX_MODEL_ANALYSIS",
    "GENX_MODEL_LONG_FORM",
    "GENX_MODEL_MODERATION",
    "QWEN_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_GEMINI_API_KEY",
    "FIRECRAWL_API_KEY",
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_BEARER_TOKEN",
    "META_APP_ID",
    "META_APP_SECRET",
    "LINKEDIN_CLIENT_ID",
    "LINKEDIN_CLIENT_SECRET",
    "TIKTOK_CLIENT_KEY",
    "TIKTOK_CLIENT_SECRET",
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "PINTEREST_CLIENT_ID",
    "PINTEREST_CLIENT_SECRET",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "SNAPCHAT_CLIENT_ID",
    "SNAPCHAT_CLIENT_SECRET",
    "BLUESKY_IDENTIFIER",
    "BLUESKY_APP_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHANNEL_ID",
    "ENCRYPTION_KEY",
    "JWT_SECRET",
    "STRIPE_SECRET_KEY",
    "RESEND_API_KEY",
}


@router.get("/system-keys")
async def list_system_keys(
    _admin: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """
    List which system API keys are currently configured (values are masked).
    """
    keys: dict[str, str] = {}
    for k in sorted(_ALLOWED_SYSTEM_KEYS):
        val = getattr(settings, k, "") or os.environ.get(k, "")
        if val:
            # Show only first 6 chars + mask
            keys[k] = val[:6] + "…" + val[-2:] if len(val) > 8 else "***"
        else:
            keys[k] = ""
    return {"keys": keys}


@router.post("/system-keys")
async def set_system_key(
    body: SystemKeyUpdate,
    _admin: User = Depends(get_admin_user),
) -> dict[str, str]:
    """
    Set a system-level API key at runtime.

    **Note**: changes are applied to the running process only.
    Persist them in your `.env` file for permanence.
    """
    if body.key_name not in _ALLOWED_SYSTEM_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Key '{body.key_name}' is not allowed. "
                   f"Allowed keys: {sorted(_ALLOWED_SYSTEM_KEYS)}",
        )
    # Update environment variable (affects this process)
    os.environ[body.key_name] = body.key_value
    # Also update the pydantic settings object directly
    try:
        object.__setattr__(settings, body.key_name, body.key_value)
    except Exception:
        pass

    return {"message": f"{body.key_name} updated successfully (runtime only – update .env to persist)"}


# ---------------------------------------------------------------------------
# Feature flag management
# ---------------------------------------------------------------------------

@router.patch("/feature-flags")
async def update_feature_flags(
    body: FeatureFlagUpdate,
    _admin: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Toggle feature flags at runtime."""
    mapping = {
        "enable_auto_post": "ENABLE_AUTO_POST",
        "enable_auto_reply": "ENABLE_AUTO_REPLY",
        "enable_ab_testing": "ENABLE_AB_TESTING",
        "enable_viral_prediction": "ENABLE_VIRAL_PREDICTION",
        "enable_cost_tracking": "ENABLE_COST_TRACKING",
        "max_content_per_day": "MAX_CONTENT_PER_DAY",
        "max_engagement_replies_per_day": "MAX_ENGAGEMENT_REPLIES_PER_DAY",
    }
    updated: dict[str, Any] = {}
    for field, setting_name in mapping.items():
        val = getattr(body, field)
        if val is not None:
            os.environ[setting_name] = str(val)
            try:
                object.__setattr__(settings, setting_name, val)
            except Exception:
                pass
            updated[field] = val

    return {"updated": updated, "message": "Feature flags updated (runtime – update .env to persist)"}


# ---------------------------------------------------------------------------
# Manual content generation trigger
# ---------------------------------------------------------------------------

@router.post("/trigger-generation")
async def trigger_generation(
    body: TriggerGenerationRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """
    Manually trigger a content generation run.
    Useful for testing or bootstrapping a new user.
    """
    from app.workers.tasks import run_content_generation_and_post

    # Fire async Celery task
    task = run_content_generation_and_post.delay(window=body.window)

    return {
        "message": "Content generation triggered",
        "task_id": task.id,
        "window": body.window,
        "target_user": body.user_id or "all",
    }


# ---------------------------------------------------------------------------
# User management (read-only overview)
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> list[dict[str, Any]]:
    """List all users with basic stats."""
    users = db.query(User).all()
    result = []
    for u in users:
        posted = (
            db.query(func.count(Content.id))
            .filter(Content.user_id == u.id, Content.status == ContentStatus.POSTED)
            .scalar()
            or 0
        )
        result.append(
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "plan": u.plan.value if u.plan else "free",
                "monthly_content_used": u.monthly_content_used,
                "monthly_content_quota": u.monthly_content_quota,
                "total_posted": posted,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
        )
    return result
