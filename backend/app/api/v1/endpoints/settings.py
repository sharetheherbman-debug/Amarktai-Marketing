"""
Settings endpoint — user preferences, API keys, billing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_api_key import UserAPIKey
from app.services.genx_client import GenXClient
from app.services.posting_readiness import PLATFORM_KEYS, publishing_readiness

logger = logging.getLogger(__name__)
router = APIRouter()
_GENX_LAST_TEST_STATE: dict[str, dict[str, Any]] = {}


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
    "GENX_BASE_URL",
    "GENX_DEFAULT_MODEL",
    "GENX_MODEL_COPY",
    "GENX_MODEL_STRATEGY",
    "GENX_MODEL_ANALYSIS",
    "GENX_MODEL_LONG_FORM",
    "GENX_MODEL_MODERATION",
    "GENX_MODEL_FALLBACKS",
    "GENX_MODEL_ALLOWLIST",
    "QWEN_API_KEY",
    "HUGGINGFACE_TOKEN",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "FIRECRAWL_API_KEY",
    "RESEND_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
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


def _provider_state(configured: bool) -> str:
    return "configured" if configured else "not_configured"


def _is_oauth_configured(client_id: str | None, client_secret: str | None) -> bool:
    return bool((client_id or "").strip() and (client_secret or "").strip())


def _active_key_rows(db: Session, user_id: str) -> dict[str, UserAPIKey]:
    rows = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == user_id,
        UserAPIKey.is_active == True,
    ).all()
    return {r.key_name: r for r in rows}


def _get_key_or_env(db_keys: dict[str, UserAPIKey], key_name: str, env_value: str = "") -> str:
    row = db_keys.get(key_name)
    if row:
        try:
            return row.get_decrypted_key()
        except Exception:
            return ""
    return env_value or ""


def _genx_task_models() -> dict[str, str]:
    return {
        "copy": settings.GENX_MODEL_COPY or "",
        "strategy": settings.GENX_MODEL_STRATEGY or "",
        "analysis": settings.GENX_MODEL_ANALYSIS or "",
        "long_form": settings.GENX_MODEL_LONG_FORM or "",
        "moderation": settings.GENX_MODEL_MODERATION or "",
        "image": getattr(settings, "GENX_MODEL_IMAGE", "") or "",
        "video": getattr(settings, "GENX_MODEL_VIDEO", "") or "",
        "audio": getattr(settings, "GENX_MODEL_AUDIO", "") or "",
    }


def _configured_genx_models() -> dict[str, Any]:
    default_model = settings.GENX_DEFAULT_MODEL or ""
    task_models = _genx_task_models()
    fallback_models = [m.strip() for m in (settings.GENX_MODEL_FALLBACKS or "").split(",") if m.strip()]
    allowlist = [m.strip() for m in (settings.GENX_MODEL_ALLOWLIST or "").split(",") if m.strip()]
    return {
        "default_model": default_model,
        "task_models": task_models,
        "fallback_models": fallback_models,
        "allowlist": allowlist,
    }


@router.get("/genx/models")
async def get_genx_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    db_keys = _active_key_rows(db, current_user.id)
    genx_key = _get_key_or_env(db_keys, "GENX_API_KEY", settings.GENX_API_KEY)
    base_url = settings.GENX_BASE_URL
    configured = _configured_genx_models()
    client = GenXClient(api_key=genx_key, base_url=base_url, default_model=configured["default_model"])

    available = await client.list_models()
    source = available.get("source", "configured_env")
    available_models = available.get("models", [])
    if not available_models:
        seeded = [configured["default_model"], *configured["fallback_models"], *configured["allowlist"], *configured["task_models"].values()]
        available_models = sorted({m for m in seeded if m})

    return {
        "configured": bool(genx_key and base_url and configured["default_model"]),
        "base_url": base_url,
        "default_model": configured["default_model"],
        "task_models": configured["task_models"],
        "fallback_models": configured["fallback_models"],
        "allowlist": configured["allowlist"],
        "available_models": available_models,
        "source": source,
        "error": available.get("error"),
    }


@router.post("/genx/test-models")
async def test_genx_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    db_keys = _active_key_rows(db, current_user.id)
    genx_key = _get_key_or_env(db_keys, "GENX_API_KEY", settings.GENX_API_KEY)
    configured = _configured_genx_models()
    client = GenXClient(
        api_key=genx_key,
        base_url=settings.GENX_BASE_URL,
        default_model=configured["default_model"],
    )

    checks: list[tuple[str, str]] = [("default", configured["default_model"])]
    for task, model in configured["task_models"].items():
        if model:
            checks.append((task, model))
    for model in configured["fallback_models"]:
        checks.append(("fallback", model))
    if configured["allowlist"]:
        for model in configured["allowlist"]:
            checks.append(("allowlist", model))

    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for task, model in checks:
        key = (task, model)
        if not model or key in seen:
            continue
        seen.add(key)
        deduped.append((task, model))

    results: list[dict[str, Any]] = []
    for task, model in deduped:
        try:
            result = await client.test_model(model=model, task=task if task != "default" else "copy")
            result["task"] = task
            results.append(result)
        except Exception:
            results.append({
                "model": model,
                "task": task,
                "ok": False,
                "latency_ms": 0,
                "error": "Model test failed",
                "sample_hash": "",
                "sample_preview": "",
            })

    required_slots = {"default", "copy", "strategy", "analysis"}
    required_models_ok = all(
        any(r["task"] == slot and r["ok"] for r in results)
        for slot in required_slots
        if slot != "default" or configured["default_model"]
    )
    failed_models = [r for r in results if not r["ok"]]
    checked_at = datetime.now(timezone.utc).isoformat()
    _GENX_LAST_TEST_STATE[current_user.id] = {
        "checked_at": checked_at,
        "required_models_ok": required_models_ok,
        "failed_models": failed_models,
        "models_tested": bool(results),
    }
    return {
        "configured": client.ready,
        "checked_at": checked_at,
        "models_tested": len(results),
        "required_models_ok": required_models_ok,
        "failed_models": failed_models,
        "results": results,
    }


@router.get("/readiness")
async def get_readiness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.core.config import settings

    db_keys = _active_key_rows(db, current_user.id)
    user_keys = set(db_keys.keys())

    genx_key = _get_key_or_env(db_keys, "GENX_API_KEY", settings.GENX_API_KEY)
    genx_configured = bool(genx_key and settings.GENX_BASE_URL and settings.GENX_DEFAULT_MODEL)
    firecrawl_configured = bool(settings.FIRECRAWL_API_KEY or "FIRECRAWL_API_KEY" in user_keys)
    email_configured = bool(settings.RESEND_API_KEY)
    stripe_configured = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)

    oauth_states = {
        "youtube": _provider_state(_is_oauth_configured(settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET)),
        "tiktok": _provider_state(_is_oauth_configured(settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET)),
        "facebook": _provider_state(_is_oauth_configured(settings.META_APP_ID, settings.META_APP_SECRET)),
        "instagram": _provider_state(_is_oauth_configured(settings.META_APP_ID, settings.META_APP_SECRET)),
        "twitter": _provider_state(_is_oauth_configured(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET)),
        "linkedin": _provider_state(_is_oauth_configured(settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET)),
        "pinterest": _provider_state(_is_oauth_configured(settings.PINTEREST_CLIENT_ID, settings.PINTEREST_CLIENT_SECRET)),
        "reddit": _provider_state(_is_oauth_configured(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET)),
        "snapchat": _provider_state(_is_oauth_configured(settings.SNAPCHAT_CLIENT_ID, settings.SNAPCHAT_CLIENT_SECRET)),
    }

    db_state = "not_configured"
    try:
        db.execute(sql_text("SELECT 1"))
        db_state = "configured"
    except Exception:
        db_state = "not_configured"

    celery_state = _provider_state(bool(settings.REDIS_URL))
    genx_client = GenXClient(api_key=genx_key)
    genx_health = await genx_client.health_check()
    genx_last = _GENX_LAST_TEST_STATE.get(current_user.id, {})
    genx_failed_models = genx_last.get("failed_models", [])
    genx_required_models_ok = bool(genx_last.get("required_models_ok")) if genx_last else bool(genx_health.get("ok"))
    posting = publishing_readiness(db, current_user.id)

    providers = {
        "genx": _provider_state(genx_configured),
        "firecrawl": _provider_state(firecrawl_configured),
        "email": _provider_state(email_configured),
        "stripe": _provider_state(stripe_configured),
        "database": db_state,
        "scheduler_celery": celery_state,
    }

    checklist = [
        {"key": "genx", "label": "GenX AI provider", "status": providers["genx"], "required": True},
        {"key": "firecrawl", "label": "Firecrawl/scraper intelligence", "status": providers["firecrawl"], "required": False},
        {"key": "database", "label": "Database health", "status": providers["database"], "required": True},
        {"key": "scheduler_celery", "label": "Scheduler/Celery", "status": providers["scheduler_celery"], "required": False},
        {"key": "email", "label": "Email provider", "status": providers["email"], "required": False},
        {"key": "stripe", "label": "Stripe billing", "status": providers["stripe"], "required": False},
    ]

    missing_required = [c["label"] for c in checklist if c["required"] and c["status"] != "configured"]
    if not genx_required_models_ok:
        missing_required.append("GenX required models")

    return {
        "providers": providers,
        "oauth": oauth_states,
        "checklist": checklist,
        "genx": {
            "configured": genx_configured,
            "health_ok": bool(genx_health.get("ok")),
            "models_tested": bool(genx_last.get("models_tested", False)),
            "required_models_ok": genx_required_models_ok,
            "failed_models": genx_failed_models,
            "last_checked_at": genx_last.get("checked_at"),
        },
        "social_platforms": {k: posting["platforms"].get(k) for k in PLATFORM_KEYS},
        "missing_required": missing_required,
        "go_live_ready": len(missing_required) == 0 and genx_required_models_ok,
    }
