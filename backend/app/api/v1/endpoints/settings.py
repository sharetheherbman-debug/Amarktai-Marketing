"""
Settings endpoint — user preferences, provider keys, readiness, and billing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.user_api_key import UserAPIKey
from app.services.genx_client import GenXClient
from app.services.posting_readiness import PLATFORM_KEYS, publishing_readiness
from app.services.provider_catalog import (
    GLOBAL_ENV_KEYS,
    USER_PROVIDER_KEYS,
    USER_PROVIDER_KEY_NAMES,
    mask_value,
    resolve_user_api_key,
)
from app.services.scraper import test_firecrawl_key

logger = logging.getLogger(__name__)
router = APIRouter()
_GENX_LAST_TEST_STATE: dict[str, dict[str, Any]] = {}
_FIRECRAWL_LAST_TEST_STATE: dict[str, dict[str, Any]] = {}


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


class APIKeyTestRequest(BaseModel):
    key_name: str
    key_value: str | None = None


class FirecrawlTestRequest(BaseModel):
    key_value: str | None = None


def _provider_state(configured: bool) -> str:
    return "configured" if configured else "not_configured"


def _test_state(configured: bool, *, ok: bool | None = None) -> str:
    if not configured:
        return "missing"
    if ok is True:
        return "test_passed"
    if ok is False:
        return "test_failed"
    return "configured"


def _is_oauth_configured(client_id: str | None, client_secret: str | None) -> bool:
    return bool((client_id or "").strip() and (client_secret or "").strip())


def _active_key_rows(db: Session, user_id: str) -> dict[str, UserAPIKey]:
    rows = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == user_id,
        UserAPIKey.is_active == True,
    ).all()
    return {r.key_name: r for r in rows}


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


async def _run_genx_test(api_key: str) -> dict[str, Any]:
    configured = _configured_genx_models()
    client = GenXClient(
        api_key=api_key,
        base_url=settings.GENX_BASE_URL,
        default_model=configured["default_model"],
    )
    health = await client.health_check()
    return {
        "ok": bool(health.get("ok")),
        "error": health.get("error"),
        "latency_ms": health.get("latency_ms", 0),
        "model": health.get("model") or configured["default_model"],
        "base_url": settings.GENX_BASE_URL,
    }


def _record_firecrawl_test(user_id: str, *, ok: bool, error: str = "") -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    _FIRECRAWL_LAST_TEST_STATE[user_id] = {
        "checked_at": checked_at,
        "ok": ok,
        "error": error,
    }
    return _FIRECRAWL_LAST_TEST_STATE[user_id]


@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
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


@router.put("")
async def update_settings(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.timezone is not None:
        current_user.timezone = payload.timezone
    if payload.language is not None:
        current_user.preferred_language = payload.language
    prefs: dict[str, Any] = current_user.notification_preferences or {}
    if payload.notification_email is not None:
        prefs["email"] = payload.notification_email
    if payload.notification_digest is not None:
        prefs["digest"] = payload.notification_digest
    current_user.notification_preferences = prefs
    if payload.auto_post_enabled is not None:
        current_user.auto_post_enabled = payload.auto_post_enabled
    if payload.auto_reply_enabled is not None:
        current_user.auto_reply_enabled = payload.auto_reply_enabled
    db.commit()
    db.refresh(current_user)
    return {"ok": True}


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = _active_key_rows(db, current_user.id)

    user_keys: list[dict[str, Any]] = []
    legacy_keys: dict[str, dict[str, Any]] = {}
    for spec in USER_PROVIDER_KEYS:
        row = rows.get(spec["key_name"])
        user_value = ""
        if row:
            try:
                user_value = row.get_decrypted_key()
            except Exception:
                user_value = ""
        env_value = getattr(settings, spec["key_name"], "") or ""
        item = {
            **spec,
            "configured": bool(user_value),
            "masked": mask_value(user_value),
            "source": "user" if user_value else "missing",
            "effective_configured": bool(user_value or env_value),
            "effective_source": "user" if user_value else ("env" if env_value else "missing"),
        }
        user_keys.append(item)
        legacy_keys[spec["key_name"]] = {
            "configured": item["configured"],
            "masked": item["masked"],
            "effective_configured": item["effective_configured"],
            "effective_source": item["effective_source"],
        }

    global_keys: list[dict[str, Any]] = []
    for spec in GLOBAL_ENV_KEYS:
        value = getattr(settings, spec["key_name"], "") or ""
        global_keys.append(
            {
                **spec,
                "configured": bool(value),
                "masked": mask_value(value, secret=spec.get("secret", True)),
                "source": "env" if value else "missing",
            }
        )

    return {
        "keys": legacy_keys,
        "user_keys": user_keys,
        "global_keys": global_keys,
    }


@router.put("/api-keys")
async def update_api_keys(
    payload: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.key_name not in USER_PROVIDER_KEY_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown key_name '{payload.key_name}'. Allowed: {sorted(USER_PROVIDER_KEY_NAMES)}",
        )
    key_value = payload.key_value.strip()
    if not key_value:
        raise HTTPException(status_code=400, detail="Key value cannot be empty.")

    enc = UserAPIKey.encrypt_key(key_value)
    row = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.key_name == payload.key_name,
    ).first()
    if row:
        row.encrypted_key = enc
        row.is_active = True
    else:
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


@router.post("/api-keys/test")
async def test_api_key(
    payload: APIKeyTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.key_name not in USER_PROVIDER_KEY_NAMES:
        raise HTTPException(status_code=400, detail="Unsupported provider key.")

    key_value = (payload.key_value or "").strip() or resolve_user_api_key(
        db,
        current_user.id,
        payload.key_name,
        getattr(settings, payload.key_name, "") or "",
    )

    if not key_value:
        return {"key_name": payload.key_name, "ok": False, "status": "missing", "error": "Provider key is missing."}

    if payload.key_name == "GENX_API_KEY":
        result = await _run_genx_test(key_value)
        return {
            "key_name": payload.key_name,
            "ok": result["ok"],
            "status": _test_state(True, ok=result["ok"]),
            "error": result["error"],
            "latency_ms": result["latency_ms"],
            "model": result["model"],
            "base_url": result["base_url"],
        }

    if payload.key_name == "FIRECRAWL_API_KEY":
        result = await test_firecrawl_key(key_value)
        recorded = _record_firecrawl_test(current_user.id, ok=bool(result["ok"]), error=str(result.get("error") or ""))
        return {
            "key_name": payload.key_name,
            "ok": bool(result["ok"]),
            "status": _test_state(True, ok=bool(result["ok"])),
            "error": result.get("error"),
            "checked_at": recorded["checked_at"],
        }

    return {
        "key_name": payload.key_name,
        "ok": True,
        "status": "configured",
        "error": None,
        "message": "Stored successfully. Live smoke test is not implemented for this optional fallback provider.",
    }


@router.get("/billing")
async def get_billing(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
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


@router.get("/genx/models")
async def get_genx_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    genx_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    configured = _configured_genx_models()
    client = GenXClient(api_key=genx_key, base_url=settings.GENX_BASE_URL, default_model=configured["default_model"])

    available = await client.list_models()
    source = available.get("source", "configured_env")
    available_models = available.get("models", [])
    if not available_models:
        seeded = [configured["default_model"], *configured["fallback_models"], *configured["allowlist"], *configured["task_models"].values()]
        available_models = sorted({m for m in seeded if m})

    return {
        "configured": bool(genx_key and settings.GENX_BASE_URL and configured["default_model"]),
        "base_url": settings.GENX_BASE_URL,
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
    genx_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
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
            results.append(
                {
                    "model": model,
                    "task": task,
                    "ok": False,
                    "latency_ms": 0,
                    "error": "Model test failed",
                    "sample_hash": "",
                    "sample_preview": "",
                }
            )

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


@router.post("/firecrawl/test")
async def firecrawl_test(
    payload: FirecrawlTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    firecrawl_key = (payload.key_value or "").strip() or resolve_user_api_key(
        db,
        current_user.id,
        "FIRECRAWL_API_KEY",
        settings.FIRECRAWL_API_KEY,
    )
    if not firecrawl_key:
        return {"ok": False, "status": "missing", "error": "Firecrawl API key is missing."}
    result = await test_firecrawl_key(firecrawl_key)
    recorded = _record_firecrawl_test(current_user.id, ok=bool(result["ok"]), error=str(result.get("error") or ""))
    return {
        "ok": bool(result["ok"]),
        "status": _test_state(True, ok=bool(result["ok"])),
        "error": result.get("error"),
        "checked_at": recorded["checked_at"],
    }


@router.get("/readiness")
async def get_readiness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    genx_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    firecrawl_key = resolve_user_api_key(db, current_user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY)
    genx_configured = bool(genx_key and settings.GENX_BASE_URL and settings.GENX_DEFAULT_MODEL)
    firecrawl_configured = bool(firecrawl_key)
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
    genx_health = await _run_genx_test(genx_key) if genx_configured else {"ok": False, "error": "GenX is not configured"}
    genx_last = _GENX_LAST_TEST_STATE.get(current_user.id, {})
    if firecrawl_configured:
        firecrawl_probe = await test_firecrawl_key(firecrawl_key)
        firecrawl_last = _record_firecrawl_test(
            current_user.id,
            ok=bool(firecrawl_probe["ok"]),
            error=str(firecrawl_probe.get("error") or ""),
        )
    else:
        firecrawl_last = _FIRECRAWL_LAST_TEST_STATE.get(current_user.id, {})
    genx_required_models_ok = bool(genx_last.get("required_models_ok")) if genx_last else bool(genx_health.get("ok"))
    posting = publishing_readiness(db, current_user.id)

    provider_details = {
        "genx": {
            "required": True,
            "source": "user" if resolve_user_api_key(db, current_user.id, "GENX_API_KEY") else ("env" if settings.GENX_API_KEY else "missing"),
            "status": _test_state(genx_configured, ok=bool(genx_health.get("ok")) if genx_configured else None),
            "message": genx_health.get("error") if genx_configured and not genx_health.get("ok") else None,
        },
        "firecrawl": {
            "required": True,
            "source": "user" if resolve_user_api_key(db, current_user.id, "FIRECRAWL_API_KEY") else ("env" if settings.FIRECRAWL_API_KEY else "missing"),
            "status": _test_state(
                firecrawl_configured,
                ok=firecrawl_last.get("ok") if firecrawl_last else None,
            ),
            "message": firecrawl_last.get("error") if firecrawl_last and not firecrawl_last.get("ok") else None,
        },
        "qwen": {
            "required": False,
            "source": "user" if resolve_user_api_key(db, current_user.id, "QWEN_API_KEY") else ("env" if settings.QWEN_API_KEY else "missing"),
            "status": _test_state(bool(resolve_user_api_key(db, current_user.id, "QWEN_API_KEY", settings.QWEN_API_KEY))),
        },
        "huggingface": {
            "required": False,
            "source": "user" if resolve_user_api_key(db, current_user.id, "HUGGINGFACE_TOKEN") else ("env" if settings.HUGGINGFACE_TOKEN else "missing"),
            "status": _test_state(bool(resolve_user_api_key(db, current_user.id, "HUGGINGFACE_TOKEN", settings.HUGGINGFACE_TOKEN))),
        },
        "openai": {
            "required": False,
            "source": "user" if resolve_user_api_key(db, current_user.id, "OPENAI_API_KEY") else ("env" if settings.OPENAI_API_KEY else "missing"),
            "status": _test_state(bool(resolve_user_api_key(db, current_user.id, "OPENAI_API_KEY", settings.OPENAI_API_KEY))),
        },
        "gemini": {
            "required": False,
            "source": "user" if resolve_user_api_key(db, current_user.id, "GEMINI_API_KEY") else ("env" if settings.GEMINI_API_KEY else "missing"),
            "status": _test_state(bool(resolve_user_api_key(db, current_user.id, "GEMINI_API_KEY", settings.GEMINI_API_KEY))),
        },
    }

    providers = {name: detail["status"] for name, detail in provider_details.items()}
    providers["email"] = _provider_state(email_configured)
    providers["stripe"] = _provider_state(stripe_configured)
    providers["database"] = db_state
    providers["scheduler_celery"] = celery_state

    checklist = [
        {"key": "genx", "label": "GenX AI provider", "status": provider_details["genx"]["status"], "required": True},
        {"key": "firecrawl", "label": "Firecrawl scraper", "status": provider_details["firecrawl"]["status"], "required": True},
        {"key": "database", "label": "Database health", "status": providers["database"], "required": True},
        {"key": "scheduler_celery", "label": "Scheduler/Celery", "status": providers["scheduler_celery"], "required": False},
        {"key": "email", "label": "Email provider", "status": providers["email"], "required": False},
        {"key": "stripe", "label": "Stripe billing", "status": providers["stripe"], "required": False},
    ]

    missing_required = [c["label"] for c in checklist if c["required"] and c["status"] not in {"configured", "test_passed"}]
    if not genx_required_models_ok:
        missing_required.append("GenX required models")

    return {
        "providers": providers,
        "provider_details": provider_details,
        "oauth": oauth_states,
        "checklist": checklist,
        "genx": {
            "configured": genx_configured,
            "health_ok": bool(genx_health.get("ok")),
            "models_tested": bool(genx_last.get("models_tested", False)),
            "required_models_ok": genx_required_models_ok,
            "failed_models": genx_last.get("failed_models", []),
            "last_checked_at": genx_last.get("checked_at"),
            "status": provider_details["genx"]["status"],
        },
        "firecrawl": {
            "configured": firecrawl_configured,
            "status": provider_details["firecrawl"]["status"],
            "last_checked_at": firecrawl_last.get("checked_at"),
            "error": firecrawl_last.get("error"),
        },
        "social_platforms": {k: posting["platforms"].get(k) for k in PLATFORM_KEYS},
        "missing_required": missing_required,
        "go_live_ready": len(missing_required) == 0 and genx_required_models_ok,
    }
