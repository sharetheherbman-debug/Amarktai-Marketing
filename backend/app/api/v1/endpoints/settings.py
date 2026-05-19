"""
Settings endpoint — user preferences, provider keys, readiness, and billing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
import httpx

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


def _safe_preview(value: str | None, limit: int = 300) -> str:
    if not value:
        return ""
    return str(value).replace("\n", " ").strip()[:limit]


def _extract_genx_text(data: dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return ""
    paths = [
        ("choices", 0, "message", "content"),
        ("choices", 0, "text"),
        ("output_text",),
        ("output",),
        ("response",),
        ("content",),
        ("text",),
        ("data", "output"),
        ("data", "text"),
        ("data", "content"),
        ("result",),
        ("result", "text"),
        ("result", "content"),
    ]
    for path in paths:
        current: Any = data
        ok = True
        for key in path:
            if isinstance(key, int):
                if isinstance(current, list) and len(current) > key:
                    current = current[key]
                else:
                    ok = False
                    break
            else:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    ok = False
                    break
        if ok and isinstance(current, str) and current.strip():
            return current.strip()
    return ""


def _resolve_provider_key(db: Session, user_id: str, key_name: str, env_value: str | None = None) -> tuple[str, str]:
    row = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == user_id,
        UserAPIKey.key_name == key_name,
        UserAPIKey.is_active == True,
    ).first()
    if row:
        try:
            key = row.get_decrypted_key()
            if key:
                return key, "user"
        except Exception:
            pass
    if env_value:
        return env_value, "env"
    return "", "missing"


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
    genx_key, genx_source = _resolve_provider_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    firecrawl_key, firecrawl_source = _resolve_provider_key(db, current_user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY)
    genx_configured = bool(genx_key and settings.GENX_BASE_URL and settings.GENX_DEFAULT_MODEL)
    firecrawl_configured = bool(firecrawl_key)

    genx_health = {"ok": False, "error": "GenX is not configured"}
    if genx_configured:
        try:
            genx_health = await _run_genx_test(genx_key)
        except Exception as exc:
            logger.warning("GenX readiness check failed for user %s: %s", current_user.id, type(exc).__name__)
            genx_health = {"ok": False, "error": "GenX check failed."}

    firecrawl_probe = {"ok": False, "error": "Firecrawl is not configured"}
    if firecrawl_configured:
        try:
            firecrawl_probe = await test_firecrawl_key(firecrawl_key)
        except Exception as exc:
            logger.warning("Firecrawl readiness check failed for user %s: %s", current_user.id, type(exc).__name__)
            firecrawl_probe = {"ok": False, "error": "Firecrawl check failed."}
    firecrawl_last = _record_firecrawl_test(
        current_user.id,
        ok=bool(firecrawl_probe.get("ok")),
        error=str(firecrawl_probe.get("error") or ""),
    )

    try:
        db.execute(sql_text("SELECT 1"))
        db_state = "configured"
    except Exception:
        db_state = "not_configured"

    posting = {"platforms": {}}
    try:
        posting = publishing_readiness(db, current_user.id)
    except Exception:
        posting = {"platforms": {}}

    oauth_states = {
        "youtube": _provider_state(_is_oauth_configured(settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET)),
        "tiktok": _provider_state(_is_oauth_configured(settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET)),
        "facebook": _provider_state(_is_oauth_configured(settings.META_APP_ID, settings.META_APP_SECRET)),
        "instagram": _provider_state(_is_oauth_configured(settings.META_APP_ID, settings.META_APP_SECRET)),
        "twitter": _provider_state(_is_oauth_configured(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET)),
        "linkedin": _provider_state(_is_oauth_configured(settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET)),
        "pinterest": _provider_state(_is_oauth_configured(settings.PINTEREST_CLIENT_ID, settings.PINTEREST_CLIENT_SECRET)),
        "reddit": _provider_state(_is_oauth_configured(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET)),
    }

    provider_details = {
        "genx": {
            "required": True,
            "source": genx_source,
            "status": _test_state(genx_configured, ok=bool(genx_health.get("ok")) if genx_configured else None),
            "message": None if bool(genx_health.get("ok")) else ("GenX check failed." if genx_configured else "GenX is not configured."),
        },
        "firecrawl": {
            "required": True,
            "source": firecrawl_source,
            "status": _test_state(firecrawl_configured, ok=bool(firecrawl_probe.get("ok")) if firecrawl_configured else None),
            "message": None if bool(firecrawl_probe.get("ok")) else ("Firecrawl check failed." if firecrawl_configured else "Firecrawl is not configured."),
        },
    }
    providers = {name: detail["status"] for name, detail in provider_details.items()}
    providers["database"] = db_state
    providers["scheduler_celery"] = _provider_state(bool(settings.REDIS_URL))

    platform_generation = {k: True for k in PLATFORM_KEYS}
    posting_readiness = {}
    for platform in PLATFORM_KEYS:
        state = posting.get("platforms", {}).get(platform, {}) if isinstance(posting, dict) else {}
        posting_readiness[platform] = {
            "can_post_now": bool(state.get("can_post_now", False)),
            "blockers": state.get("missing", ["oauth_not_configured"]) if isinstance(state, dict) else ["oauth_not_configured"],
        }

    generation_readiness = {
        "genx": provider_details["genx"]["status"],
        "firecrawl": provider_details["firecrawl"]["status"],
        "fallback": "configured",
        "can_generate_beta": True,
    }
    scraping_readiness = {
        "firecrawl": provider_details["firecrawl"]["status"],
        "fallback_scraper_available": True,
    }

    missing_required = []
    if db_state != "configured":
        missing_required.append("Database health")

    beta_go_ready = True
    full_go_live_ready = (
        provider_details["genx"]["status"] == "test_passed"
        and provider_details["firecrawl"]["status"] == "test_passed"
    )

    checklist = [
        {"key": "genx", "label": "GenX AI provider", "status": provider_details["genx"]["status"], "required": False},
        {"key": "firecrawl", "label": "Firecrawl scraper", "status": provider_details["firecrawl"]["status"], "required": False},
        {"key": "database", "label": "Database health", "status": providers["database"], "required": True},
    ]

    return {
        "providers": providers,
        "provider_details": provider_details,
        "oauth": oauth_states,
        "checklist": checklist,
        "genx": {
            "configured": genx_configured,
            "health_ok": bool(genx_health.get("ok")),
            "models_tested": bool(_GENX_LAST_TEST_STATE.get(current_user.id, {}).get("models_tested", False)),
            "required_models_ok": bool(_GENX_LAST_TEST_STATE.get(current_user.id, {}).get("required_models_ok", genx_health.get("ok"))),
            "failed_models": _GENX_LAST_TEST_STATE.get(current_user.id, {}).get("failed_models", []),
            "last_checked_at": _GENX_LAST_TEST_STATE.get(current_user.id, {}).get("checked_at"),
            "status": provider_details["genx"]["status"],
        },
        "firecrawl": {
            "configured": firecrawl_configured,
            "status": provider_details["firecrawl"]["status"],
            "last_checked_at": firecrawl_last.get("checked_at"),
            "error": "Provider test failed." if provider_details["firecrawl"]["status"] == "test_failed" else None,
        },
        "social_platforms": {k: posting.get("platforms", {}).get(k, {}) for k in PLATFORM_KEYS} if isinstance(posting, dict) else {},
        "missing_required": missing_required,
        "go_live_ready": full_go_live_ready,
        "generation_readiness": generation_readiness,
        "scraping_readiness": scraping_readiness,
        "platform_generation": platform_generation,
        "posting_readiness": posting_readiness,
        "beta_go_ready": beta_go_ready,
        "full_go_live_ready": full_go_live_ready,
    }


@router.get("/provider-resolution")
async def provider_resolution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    providers = ["GENX_API_KEY", "FIRECRAWL_API_KEY", "QWEN_API_KEY", "HUGGINGFACE_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY"]
    resolved = {}
    for key_name in providers:
        key_value, source = _resolve_provider_key(db, current_user.id, key_name, getattr(settings, key_name, "") or "")
        resolved[key_name] = {
            "effective_source": source,
            "masked_value": mask_value(key_value),
        }
    return {"providers": resolved}


@router.post("/genx/debug-test")
async def genx_debug_test(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    api_key, source = _resolve_provider_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    base_url = settings.GENX_BASE_URL
    model = settings.GENX_DEFAULT_MODEL
    if not api_key:
        return {
            "http_status": 0,
            "base_url": base_url,
            "model": model,
            "response_shape_keys": [],
            "parsed_text_present": False,
            "parsed_content_present": False,
            "sanitized_preview": "",
            "error": "GENX_API_KEY is missing.",
            "effective_source": source,
        }
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with one short sentence for debug."}],
        "max_tokens": 32,
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        raw = response.json() if "json" in (response.headers.get("content-type", "").lower()) else {"text": response.text[:500]}
        parsed = _extract_genx_text(raw if isinstance(raw, dict) else {})
        preview = _safe_preview(parsed or str(raw)[:300])
        return {
            "http_status": response.status_code,
            "base_url": base_url,
            "model": model,
            "response_shape_keys": sorted(list(raw.keys())) if isinstance(raw, dict) else [],
            "parsed_text_present": bool(parsed),
            "parsed_content_present": bool(parsed),
            "sanitized_preview": preview,
            "error": None if response.status_code < 400 and parsed else ("No response text parsed." if response.status_code < 400 else "GenX request failed."),
            "effective_source": source,
        }
    except Exception as exc:
        logger.warning("GenX debug test failed for user %s: %s", current_user.id, type(exc).__name__)
        return {
            "http_status": 0,
            "base_url": base_url,
            "model": model,
            "response_shape_keys": [],
            "parsed_text_present": False,
            "parsed_content_present": False,
            "sanitized_preview": "",
            "error": "GenX request failed.",
            "effective_source": source,
        }


@router.post("/firecrawl/debug-test")
async def firecrawl_debug_test(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    api_key, source = _resolve_provider_key(db, current_user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY)
    base_url = "https://api.firecrawl.dev/v2/scrape"
    if not api_key:
        return {
            "http_status": 0,
            "base_url": base_url,
            "response_shape_keys": [],
            "parsed_text_present": False,
            "parsed_content_present": False,
            "sanitized_preview": "",
            "error": "FIRECRAWL_API_KEY is missing.",
            "effective_source": source,
        }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                base_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"url": "https://example.com", "formats": ["markdown", "html"]},
            )
        raw = response.json() if "json" in (response.headers.get("content-type", "").lower()) else {"text": response.text[:500]}
        content = ""
        if isinstance(raw, dict):
            data = raw.get("data", {}) if isinstance(raw.get("data"), dict) else {}
            content = str(
                data.get("markdown")
                or data.get("html")
                or data.get("content")
                or raw.get("markdown")
                or raw.get("html")
                or raw.get("content")
                or ""
            )
        return {
            "http_status": response.status_code,
            "base_url": base_url,
            "response_shape_keys": sorted(list(raw.keys())) if isinstance(raw, dict) else [],
            "parsed_text_present": bool(content),
            "parsed_content_present": bool(content),
            "sanitized_preview": _safe_preview(content),
            "error": None if response.status_code < 400 else "Firecrawl request failed.",
            "effective_source": source,
        }
    except Exception as exc:
        logger.warning("Firecrawl debug test failed for user %s: %s", current_user.id, type(exc).__name__)
        return {
            "http_status": 0,
            "base_url": base_url,
            "response_shape_keys": [],
            "parsed_text_present": False,
            "parsed_content_present": False,
            "sanitized_preview": "",
            "error": "Firecrawl request failed.",
            "effective_source": source,
        }
