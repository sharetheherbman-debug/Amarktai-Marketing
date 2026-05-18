"""
Settings endpoint — user preferences, API keys, billing.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class PreferencesUpdate(BaseModel):
    timezone: str | None = None
    language: str | None = None
    notification_email: bool | None = None
    notification_digest: bool | None = None
    auto_post_enabled: bool | None = None
    auto_reply_enabled: bool | None = None


class APIKeyUpdate(BaseModel):
    key_name: str
    key_value: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mask(value: str | None) -> str:
    """Return a masked representation — never return plaintext."""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _encrypt(value: str) -> str:
    """Encrypt a plaintext value using the app encryption key."""
    from app.models.user_api_key import UserAPIKey
    return UserAPIKey.encrypt_key(value)


def _decrypt(value: str) -> str:
    """Decrypt an encrypted value."""
    from app.models.user_api_key import UserAPIKey
    return UserAPIKey.decrypt_key(value)


# ── GET /settings ─────────────────────────────────────────────────────────────

@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return current user preferences."""
    prefs = current_user.notification_preferences or {}
    return {
        "timezone": getattr(current_user, "timezone", "UTC") or "UTC",
        "language": getattr(current_user, "preferred_language", "en") or "en",
        "notification_email": prefs.get("email", True),
        "notification_digest": prefs.get("digest", True),
        "auto_post_enabled": getattr(current_user, "auto_post_enabled", False) or False,
        "auto_reply_enabled": getattr(current_user, "auto_reply_enabled", False) or False,
        "plan_tier": getattr(current_user, "plan", "free"),
    }


# ── PUT /settings ─────────────────────────────────────────────────────────────

@router.put("")
async def update_settings(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update user preferences."""
    if payload.timezone is not None:
        current_user.timezone = payload.timezone
    if payload.language is not None:
        current_user.preferred_language = payload.language
    # notification_email / notification_digest stored in notification_preferences JSON
    prefs: dict = current_user.notification_preferences or {}
    if payload.notification_email is not None:
        prefs["email"] = payload.notification_email
    if payload.notification_digest is not None:
        prefs["digest"] = payload.notification_digest
    current_user.notification_preferences = prefs
    # Automation preferences
    if payload.auto_post_enabled is not None:
        current_user.auto_post_enabled = payload.auto_post_enabled
    if payload.auto_reply_enabled is not None:
        current_user.auto_reply_enabled = payload.auto_reply_enabled
    db.commit()
    db.refresh(current_user)
    return {"ok": True}


# ── GET /settings/api-keys ────────────────────────────────────────────────────

_PROVIDER_KEYS = [
    "GENX_API_KEY",
    "QWEN_API_KEY",
    "HUGGINGFACE_TOKEN",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "FIRECRAWL_API_KEY",
]


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return masked provider key status — never plaintext."""
    from app.models.user_api_key import UserAPIKey

    rows = db.query(UserAPIKey).filter(UserAPIKey.user_id == current_user.id).all()
    stored: dict[str, str] = {r.key_name: r.encrypted_key for r in rows}

    result: dict[str, dict] = {}
    for key_name in _PROVIDER_KEYS:
        enc = stored.get(key_name, "")
        result[key_name] = {
            "configured": bool(enc),
            "masked": _mask(_decrypt(enc)) if enc else "",
        }
    return {"keys": result}


# ── PUT /settings/api-keys ────────────────────────────────────────────────────

@router.put("/api-keys")
async def update_api_keys(
    payload: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Store an encrypted provider API key."""
    if payload.key_name not in _PROVIDER_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown key_name '{payload.key_name}'. Allowed: {_PROVIDER_KEYS}",
        )
    from app.models.user_api_key import UserAPIKey

    enc = _encrypt(payload.key_value.strip())
    row = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.key_name == payload.key_name,
    ).first()
    if row:
        row.encrypted_key = enc
    else:
        import uuid
        row = UserAPIKey(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            key_name=payload.key_name,
            encrypted_key=enc,
            is_active=True,
        )
        db.add(row)
    db.commit()
    return {"ok": True, "key_name": payload.key_name}


# ── GET /settings/billing ─────────────────────────────────────────────────────

@router.get("/billing")
async def get_billing(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return plan tier and quota information."""
    plan = getattr(current_user, "plan", "free") or "free"
    quota_map = {"free": 50, "pro": 500, "business": 2000, "enterprise": 99999}
    used = getattr(current_user, "monthly_content_used", 0) or 0
    limit = quota_map.get(str(plan), 50)
    return {
        "plan_tier": str(plan),
        "quota_used": used,
        "quota_limit": limit,
        "quota_remaining": max(0, limit - used),
    }
