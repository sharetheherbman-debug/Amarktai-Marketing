"""
Settings endpoint — user preferences, provider keys, readiness, and billing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
import httpx

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.user_api_key import UserAPIKey, UserIntegration
from app.services.genx_client import GenXClient
from app.services.huggingface_task_router import HuggingFaceTaskRouter
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
    test_url: str | None = None


class HuggingFaceTaskTestRequest(BaseModel):
    task: str
    model_override: str | None = None


class PixabayTestRequest(BaseModel):
    key_value: str | None = None
    query: str | None = None


def _safe_preview(value: str | None, limit: int = 300) -> str:
    if not value:
        return ""
    return str(value).replace("\n", " ").strip()[:limit]


def _actionable_error_message(error: Any, fallback: str) -> str:
    text = _safe_preview(str(error or ""))
    return text or fallback


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


def _classify_provider_error(error_text: str | None) -> str:
    text = (error_text or "").lower()
    if not text:
        return "configured_not_tested"
    if "decrypt" in text:
        return "decrypt_failed"
    if "model" in text and ("invalid" in text or "not found" in text):
        return "model_invalid"
    if "mapping" in text:
        return "model_mapping_required"
    if "http 401" in text or "http 403" in text or "invalid key" in text or "unauthorized" in text:
        return "provider_rejected_key"
    if "http 400" in text and "url" in text:
        return "test_url_rejected"
    if "timeout" in text or "unreachable" in text or "dns" in text or "connection" in text:
        return "endpoint_unreachable"
    return "provider_error"


def _provider_next_action(*, configured: bool, decrypt_ok: bool | None, last_status: str | None) -> str:
    if not configured:
        return "Add key"
    if decrypt_ok is False:
        return "Reset key"
    if last_status in {"model_mapping_required"}:
        return "Set model mapping"
    if last_status in {"provider_rejected_key", "model_invalid"}:
        return "Replace key or model"
    if last_status in {"configured_not_tested", None}:
        return "Run provider test"
    return "Ready"


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
    effective_default = (
        default_model
        or task_models.get("copy")
        or task_models.get("strategy")
        or task_models.get("analysis")
        or (fallback_models[0] if fallback_models else "")
    )
    return {
        "default_model": default_model,
        "effective_default_model": effective_default,
        "task_models": task_models,
        "fallback_models": fallback_models,
        "allowlist": allowlist,
    }


async def _run_genx_test(api_key: str) -> dict[str, Any]:
    configured = _configured_genx_models()
    selected_model = configured["effective_default_model"]
    if not selected_model and api_key:
        try:
            from app.services.genx_router_client import GenXRouterClient

            catalog = await GenXRouterClient(api_key=api_key, base_url=settings.GENX_BASE_URL.replace("/v1", "")).list_models()
            models = catalog.get("models") or []
            parsed_ids: list[str] = []
            for model in models:
                if isinstance(model, dict):
                    model_id = str(model.get("id") or model.get("model") or "").strip()
                    category = str(model.get("category") or "").lower()
                    if model_id and (category in {"text", "chat"} or "chat" in model_id.lower() or "text" in model_id.lower()):
                        parsed_ids.append(model_id)
                elif isinstance(model, str):
                    parsed_ids.append(model)
            selected_model = parsed_ids[0] if parsed_ids else ""
        except Exception:
            selected_model = ""
    if not selected_model:
        return {
            "ok": False,
            "error": "model_mapping_required",
            "latency_ms": 0,
            "model": "",
            "base_url": settings.GENX_BASE_URL,
        }
    client = GenXClient(
        api_key=api_key,
        base_url=settings.GENX_BASE_URL,
        default_model=selected_model,
    )
    health = await client.health_check()
    return {
        "ok": bool(health.get("ok")),
        "error": health.get("error"),
        "latency_ms": health.get("latency_ms", 0),
        "model": health.get("model") or selected_model,
        "base_url": settings.GENX_BASE_URL,
    }


def _genx_capabilities_from_config() -> dict[str, Any]:
    configured = _configured_genx_models()
    task_models = configured["task_models"]
    return {
        "text_copy": {"model": task_models.get("copy") or configured["effective_default_model"], "configured": bool(task_models.get("copy") or configured["effective_default_model"])},
        "strategy": {"model": task_models.get("strategy") or configured["effective_default_model"], "configured": bool(task_models.get("strategy") or configured["effective_default_model"])},
        "analysis": {"model": task_models.get("analysis") or configured["effective_default_model"], "configured": bool(task_models.get("analysis") or configured["effective_default_model"])},
        "image": {"model": task_models.get("image"), "configured": bool(task_models.get("image"))},
        "video": {"model": task_models.get("video"), "configured": bool(task_models.get("video"))},
        "voice": {"model": task_models.get("audio"), "configured": bool(task_models.get("audio"))},
        "avatar": {"model": task_models.get("audio"), "configured": bool(task_models.get("audio"))},
        "kling_video": {"model": task_models.get("video"), "configured": bool(task_models.get("video"))},
    }


def _record_firecrawl_test(user_id: str, *, ok: bool, error: str = "") -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    _FIRECRAWL_LAST_TEST_STATE[user_id] = {
        "checked_at": checked_at,
        "ok": ok,
        "error": error,
    }
    return _FIRECRAWL_LAST_TEST_STATE[user_id]


def _record_genx_test(user_id: str, *, ok: bool, error: str = "", model: str = "") -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    _GENX_LAST_TEST_STATE[user_id] = {
        "checked_at": checked_at,
        "ok": ok,
        "error": error,
        "model": model,
    }
    return _GENX_LAST_TEST_STATE[user_id]


def _default_firecrawl_test_url(db: Session, user_id: str) -> str | None:
    from app.models.webapp import WebApp
    business = (
        db.query(WebApp)
        .filter(WebApp.user_id == user_id)
        .order_by(WebApp.created_at.desc())
        .first()
    )
    if business and getattr(business, "url", None):
        return str(business.url).strip()
    return None


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


@router.delete("/api-keys/{key_name}")
async def delete_api_key_by_name(
    key_name: str,
    confirm: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to remove this key.")
    if key_name not in USER_PROVIDER_KEY_NAMES:
        raise HTTPException(status_code=400, detail="Unsupported provider key.")
    deleted = (
        db.query(UserAPIKey)
        .filter(
            UserAPIKey.user_id == current_user.id,
            UserAPIKey.key_name == key_name,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Removed provider key user=%s key_name=%s keys_deleted=%s", current_user.id, key_name, deleted)
    return {"key_name": key_name, "keys_deleted": int(deleted)}


@router.delete("/api-keys")
async def delete_all_api_keys(
    confirm: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to remove all provider keys.")
    deleted = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Removed all provider keys user=%s keys_deleted=%s", current_user.id, deleted)
    return {"keys_deleted": int(deleted)}


@router.post("/api-keys/reset-all")
async def reset_all_provider_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    deleted = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Reset all provider keys user=%s keys_deleted=%s", current_user.id, deleted)
    return {"keys_deleted": int(deleted)}


@router.post("/api-keys/test")
async def test_api_key(
    payload: APIKeyTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.key_name not in USER_PROVIDER_KEY_NAMES:
        raise HTTPException(status_code=400, detail="Unsupported provider key.")
    try:
        resolved_key, source = _resolve_provider_key(
            db,
            current_user.id,
            payload.key_name,
            getattr(settings, payload.key_name, "") or "",
        )
        key_value = (payload.key_value or "").strip() or resolved_key

        if not key_value:
            return {
                "key_name": payload.key_name,
                "ok": False,
                "status": "missing",
                "effective_source": "missing",
                "error": "Provider key is missing.",
            }

        if payload.key_name == "GENX_API_KEY":
            result = await _run_genx_test(key_value)
            ok = bool(result.get("ok"))
            recorded = _record_genx_test(
                current_user.id,
                ok=ok,
                error=str(result.get("error") or ""),
                model=str(result.get("model") or ""),
            )
            return {
                "key_name": payload.key_name,
                "ok": ok,
                "status": "test_passed" if ok else _classify_provider_error(str(result.get("error") or "")),
                "effective_source": source if not payload.key_value else "provided",
                "error": None if ok else _actionable_error_message(result.get("error"), "GenX provider test failed."),
                "latency_ms": result.get("latency_ms", 0),
                "model": result.get("model"),
                "base_url": result.get("base_url"),
                "checked_at": recorded["checked_at"],
            }

        if payload.key_name == "FIRECRAWL_API_KEY":
            result = await test_firecrawl_key(key_value)
            ok = bool(result.get("ok"))
            recorded = _record_firecrawl_test(current_user.id, ok=ok, error=str(result.get("error") or ""))
            return {
                "key_name": payload.key_name,
                "ok": ok,
                "status": "scrape_passed" if ok else _classify_provider_error(str(result.get("error") or "")),
                "effective_source": source if not payload.key_value else "provided",
                "error": None if ok else "Firecrawl provider test failed.",
                "checked_at": recorded["checked_at"],
            }

        return {
            "key_name": payload.key_name,
            "ok": True,
            "status": "configured",
            "effective_source": source if not payload.key_value else "provided",
            "error": None,
            "message": "Stored successfully. Live smoke test is not implemented for this optional fallback provider.",
        }
    except Exception as exc:
        logger.warning("Provider test failed for user %s key %s: %s", current_user.id, payload.key_name, type(exc).__name__)
        return {
            "key_name": payload.key_name,
            "ok": False,
            "status": "test_failed",
            "effective_source": "unknown",
            "error": "Provider test failed. Check provider configuration and retry.",
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
    client = GenXClient(api_key=genx_key, base_url=settings.GENX_BASE_URL, default_model=configured["effective_default_model"])

    available = await client.list_models()
    source = available.get("source", "configured_env")
    available_models = available.get("models", [])
    if not available_models:
        seeded = [configured["default_model"], *configured["fallback_models"], *configured["allowlist"], *configured["task_models"].values()]
        available_models = sorted({m for m in seeded if m})

    return {
        "configured": bool(genx_key and settings.GENX_BASE_URL and configured["effective_default_model"]),
        "base_url": settings.GENX_BASE_URL,
        "default_model": configured["effective_default_model"],
        "task_models": configured["task_models"],
        "fallback_models": configured["fallback_models"],
        "allowlist": configured["allowlist"],
        "available_models": available_models,
        "source": source,
        "error": available.get("error"),
    }


@router.get("/genx/capabilities")
async def get_genx_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    genx_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    configured = _configured_genx_models()
    capabilities = _genx_capabilities_from_config()
    return {
        "key_saved": bool(genx_key),
        "base_url": settings.GENX_BASE_URL,
        "default_model": configured["effective_default_model"],
        "capabilities": capabilities,
        "manual_model_config_required": not all(item["configured"] for item in capabilities.values()),
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
        "ok": required_models_ok,
        "error": None if required_models_ok else (failed_models[0].get("error") if failed_models else "Model test failed"),
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
        return {"ok": False, "status": "missing_key", "error": "Firecrawl API key is missing."}
    test_url = (payload.test_url or "").strip() or _default_firecrawl_test_url(db, current_user.id)
    if not test_url:
        return {
            "ok": False,
            "status": "no_test_url",
            "error": "Add a business URL to test Firecrawl.",
            "test_url": None,
        }
    result = await test_firecrawl_key(firecrawl_key, url=test_url)
    ok = bool(result.get("ok"))
    error_text = str(result.get("error") or "")
    recorded = _record_firecrawl_test(current_user.id, ok=ok, error=error_text)
    status_value = "scrape_passed" if ok else _classify_provider_error(error_text)
    if status_value == "test_url_rejected":
        status_value = "test_url_rejected"
    return {
        "ok": ok,
        "status": status_value,
        "error": None if ok else ("Firecrawl scrape test failed." if status_value != "no_test_url" else "Add a business URL to test Firecrawl."),
        "checked_at": recorded["checked_at"],
        "test_url": test_url,
    }


@router.get("/pixabay/status")
async def pixabay_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    key, source = _resolve_provider_key(db, current_user.id, "PIXABAY_API_KEY", settings.PIXABAY_API_KEY)
    return {
        "key_saved": source != "missing",
        "effective_source": source,
        "configured": bool(key),
        "status": "configured_not_tested" if bool(key) else "missing_key",
        "next_action": "Run Pixabay test" if bool(key) else "Add key",
    }


@router.post("/pixabay/test")
async def pixabay_test(
    payload: PixabayTestRequest = Body(default_factory=PixabayTestRequest),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    key, source = _resolve_provider_key(db, current_user.id, "PIXABAY_API_KEY", settings.PIXABAY_API_KEY)
    key_value = (payload.key_value or "").strip() or key
    if not key_value:
        return {"ok": False, "status": "missing_key", "image_api_status": "missing_key", "video_api_status": "missing_key"}
    query = (payload.query or "business marketing").strip()
    image_status = "endpoint_unreachable"
    video_status = "endpoint_unreachable"
    ok = False
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            image_resp = await client.get("https://pixabay.com/api/", params={"key": key_value, "q": query, "per_page": 3, "safesearch": "true"})
            video_resp = await client.get("https://pixabay.com/api/videos/", params={"key": key_value, "q": query, "per_page": 3, "safesearch": "true"})
        image_status = "test_passed" if image_resp.status_code < 400 else ("provider_rejected_key" if image_resp.status_code in {400, 401, 403} else "endpoint_unreachable")
        video_status = "test_passed" if video_resp.status_code < 400 else ("provider_rejected_key" if video_resp.status_code in {400, 401, 403} else "endpoint_unreachable")
        ok = image_status == "test_passed" and video_status == "test_passed"
        if not ok:
            error = f"Image HTTP {image_resp.status_code}, video HTTP {video_resp.status_code}"
    except Exception as exc:
        logger.warning("Pixabay test failed for user %s: %s", current_user.id, type(exc).__name__)
        error = "Pixabay request failed."
    return {
        "ok": ok,
        "effective_source": source if not payload.key_value else "provided",
        "status": "test_passed" if ok else _classify_provider_error(error),
        "image_api_status": image_status,
        "video_api_status": video_status,
        "error": error,
        "query": query,
    }


@router.get("/readiness")
async def get_readiness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    genx_key, genx_source = _resolve_provider_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    firecrawl_key, firecrawl_source = _resolve_provider_key(db, current_user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY)
    qwen_key, qwen_source = _resolve_provider_key(db, current_user.id, "QWEN_API_KEY", settings.QWEN_API_KEY)
    hf_token, hf_source = _resolve_provider_key(db, current_user.id, "HUGGINGFACE_TOKEN", settings.HUGGINGFACE_TOKEN)
    pixabay_key, pixabay_source = _resolve_provider_key(db, current_user.id, "PIXABAY_API_KEY", settings.PIXABAY_API_KEY)
    genx_models = _configured_genx_models()
    genx_configured = bool(genx_key and settings.GENX_BASE_URL and genx_models["effective_default_model"])
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

    genx_model_invalid = genx_configured and (not bool(genx_health.get("ok")))
    provider_details = {
        "genx": {
            "required": True,
            "source": genx_source,
            "status": "model_invalid" if genx_model_invalid else _test_state(genx_configured, ok=bool(genx_health.get("ok")) if genx_configured else None),
            "message": (
                _actionable_error_message(genx_health.get("error"), "Configured GenX model is invalid.")
                if genx_model_invalid else
                (None if bool(genx_health.get("ok")) else ("GenX check failed." if genx_configured else "GenX is not configured."))
            ),
        },
        "firecrawl": {
            "required": True,
            "source": firecrawl_source,
            "status": _test_state(firecrawl_configured, ok=bool(firecrawl_probe.get("ok")) if firecrawl_configured else None),
            "message": None if bool(firecrawl_probe.get("ok")) else ("Firecrawl check failed." if firecrawl_configured else "Firecrawl is not configured."),
        },
        "qwen": {
            "required": False,
            "source": qwen_source,
            "status": "fallback_available" if bool(qwen_key) else "missing",
            "message": "Qwen fallback available." if bool(qwen_key) else "Qwen key missing.",
        },
        "huggingface": {
            "required": False,
            "source": hf_source,
            "status": "configured" if bool(hf_token) else "missing_token",
            "message": "Token saved." if bool(hf_token) else "Missing token / add token to unlock HF tasks.",
        },
        "pixabay": {
            "required": False,
            "source": pixabay_source,
            "status": "configured_not_tested" if bool(pixabay_key) else "missing_key",
            "message": "Pixabay key saved." if bool(pixabay_key) else "Add PIXABAY_API_KEY for asset search.",
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
        "qwen": provider_details["qwen"]["status"],
        "huggingface": provider_details["huggingface"]["status"],
        "pixabay": provider_details["pixabay"]["status"],
        "fallback": "configured" if bool(qwen_key or hf_token) else "missing",
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
        {"key": "qwen", "label": "Qwen fallback", "status": provider_details["qwen"]["status"], "required": False},
        {"key": "huggingface", "label": "HuggingFace tasks", "status": provider_details["huggingface"]["status"], "required": False},
        {"key": "pixabay", "label": "Pixabay assets", "status": provider_details["pixabay"]["status"], "required": False},
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
            "model": genx_models["effective_default_model"],
            "models_tested": bool(_GENX_LAST_TEST_STATE.get(current_user.id, {}).get("models_tested", False)),
            "required_models_ok": bool(_GENX_LAST_TEST_STATE.get(current_user.id, {}).get("required_models_ok", genx_health.get("ok"))),
            "failed_models": _GENX_LAST_TEST_STATE.get(current_user.id, {}).get("failed_models", []),
            "last_checked_at": _GENX_LAST_TEST_STATE.get(current_user.id, {}).get("checked_at"),
            "status": provider_details["genx"]["status"],
            "degraded": provider_details["genx"]["status"] in {"model_invalid", "test_failed"},
            "fallback_provider": "qwen" if bool(qwen_key) else ("huggingface" if bool(hf_token) else None),
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
    providers = ["GENX_API_KEY", "FIRECRAWL_API_KEY", "QWEN_API_KEY", "HUGGINGFACE_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY", "PIXABAY_API_KEY"]
    resolved = {}
    for key_name in providers:
        # Check if a DB row exists (for decrypt_ok)
        row = db.query(UserAPIKey).filter(
            UserAPIKey.user_id == current_user.id,
            UserAPIKey.key_name == key_name,
            UserAPIKey.is_active == True,
        ).first()
        decrypt_ok: bool | None = None
        if row:
            try:
                decrypted = row.get_decrypted_key()
                decrypt_ok = bool(decrypted)
            except Exception:
                decrypt_ok = False

        key_value, source = _resolve_provider_key(db, current_user.id, key_name, getattr(settings, key_name, "") or "")
        configured = source != "missing" and bool(key_value)

        # Retrieve last test status from in-memory state if available
        last_test_status: str | None = None
        last_test_error: str | None = None
        last_test_at: str | None = None
        if key_name == "GENX_API_KEY":
            ts = _GENX_LAST_TEST_STATE.get(current_user.id, {})
            if ts.get("checked_at"):
                last_test_status = "test_passed" if ts.get("ok") else _classify_provider_error(str(ts.get("error") or ""))
                last_test_error = ts.get("error") or None
                last_test_at = ts.get("checked_at")
        elif key_name == "FIRECRAWL_API_KEY":
            ts = _FIRECRAWL_LAST_TEST_STATE.get(current_user.id, {})
            if ts.get("checked_at"):
                last_test_status = "scrape_passed" if ts.get("ok") else _classify_provider_error(str(ts.get("error") or ""))
                last_test_error = ts.get("error") or None
                last_test_at = ts.get("checked_at")

        resolved[key_name] = {
            "key_name": key_name,
            "effective_source": source,
            "masked_value": mask_value(key_value),
            "decrypt_ok": decrypt_ok,
            "configured": configured,
            "last_test_status": last_test_status,
            "last_test_error": last_test_error,
            "last_test_at": last_test_at,
            "next_action": _provider_next_action(configured=configured, decrypt_ok=decrypt_ok, last_status=last_test_status),
        }
    return {"providers": resolved}


@router.post("/reset-provider-state")
async def reset_provider_state(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    tests_cleared = 0
    mappings_deleted = 0
    if _GENX_LAST_TEST_STATE.pop(current_user.id, None) is not None:
        tests_cleared += 1
    if _FIRECRAWL_LAST_TEST_STATE.pop(current_user.id, None) is not None:
        tests_cleared += 1
    if _GENX_MODEL_MAPPING.pop(current_user.id, None) is not None:
        mappings_deleted += 1
    logger.info(
        "Reset provider state user=%s tests_cleared=%s mappings_deleted=%s",
        current_user.id,
        tests_cleared,
        mappings_deleted,
    )
    return {
        "keys_deleted": 0,
        "integrations_deleted": 0,
        "mappings_deleted": mappings_deleted,
        "tests_cleared": tests_cleared,
    }


@router.post("/reset-launch-state")
async def reset_launch_state(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    keys_deleted = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    integrations_deleted = (
        db.query(UserIntegration)
        .filter(UserIntegration.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    tests_cleared = 0
    mappings_deleted = 0
    if _GENX_LAST_TEST_STATE.pop(current_user.id, None) is not None:
        tests_cleared += 1
    if _FIRECRAWL_LAST_TEST_STATE.pop(current_user.id, None) is not None:
        tests_cleared += 1
    if _GENX_MODEL_MAPPING.pop(current_user.id, None) is not None:
        mappings_deleted += 1
    db.commit()
    logger.info(
        "Reset launch state user=%s keys_deleted=%s integrations_deleted=%s mappings_deleted=%s tests_cleared=%s",
        current_user.id,
        keys_deleted,
        integrations_deleted,
        mappings_deleted,
        tests_cleared,
    )
    return {
        "keys_deleted": int(keys_deleted),
        "integrations_deleted": int(integrations_deleted),
        "mappings_deleted": mappings_deleted,
        "tests_cleared": tests_cleared,
    }


@router.get("/providers/debug")
async def providers_debug(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Detailed provider diagnostic snapshot — no secrets returned.

    Each provider block is isolated so a single missing/broken key never
    causes a 500.  Missing keys return structured status, not exceptions.
    """
    result: dict[str, Any] = {}

    # ── GenX ──────────────────────────────────────────────────────────────────
    try:
        genx_key, genx_source = _resolve_provider_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
        genx_models_cfg = _configured_genx_models()
        genx_model_mapping_present = bool(genx_models_cfg["effective_default_model"])
        genx_ts = _GENX_LAST_TEST_STATE.get(current_user.id, {})
        result["genx"] = {
            "configured": genx_source != "missing",
            "key_saved": genx_source != "missing",
            "key_source": genx_source,
            "decrypt_ok": bool(genx_key) if genx_source == "user" else None,
            "base_url": settings.GENX_BASE_URL or None,
            "streaming_base_url": settings.GENX_BASE_URL or None,
            "model_catalog_endpoint_reachable": bool(genx_models_cfg["effective_default_model"]),
            "model_mapping_present": genx_model_mapping_present,
            "selected_text_model": genx_models_cfg["task_models"].get("copy") or genx_models_cfg["effective_default_model"] or None,
            "selected_image_model": genx_models_cfg["task_models"].get("image") or None,
            "selected_video_model": genx_models_cfg["task_models"].get("video") or None,
            "selected_voice_audio_avatar_model": genx_models_cfg["task_models"].get("audio") or None,
            "task_models": {k: v for k, v in genx_models_cfg["task_models"].items() if v},
            "last_test_status": ("test_passed" if genx_ts.get("ok") else _classify_provider_error(str(genx_ts.get("error") or ""))) if genx_ts.get("checked_at") else "configured_not_tested",
            "last_test_at": genx_ts.get("checked_at"),
            "last_test_error": genx_ts.get("error") or None,
            "last_error_classification": _classify_provider_error(str(genx_ts.get("error") or "")) if genx_ts.get("error") else None,
            "status": "missing_key" if genx_source == "missing" else ("no_model" if not genx_model_mapping_present else "configured_not_tested"),
            "note": (
                "Key missing — configure GENX_API_KEY" if genx_source == "missing"
                else ("No model configured — set GENX_DEFAULT_MODEL or a task model" if not genx_model_mapping_present else None)
            ),
        }
    except Exception as exc:
        logger.warning("providers_debug genx block error: %s", exc)
        result["genx"] = {"configured": False, "status": "provider_error", "error": _safe_preview(str(exc), 200)}

    # ── Firecrawl ─────────────────────────────────────────────────────────────
    try:
        firecrawl_key, firecrawl_source = _resolve_provider_key(db, current_user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY)
        firecrawl_ts = _FIRECRAWL_LAST_TEST_STATE.get(current_user.id, {})
        result["firecrawl"] = {
            "configured": firecrawl_source != "missing",
            "key_saved": firecrawl_source != "missing",
            "key_source": firecrawl_source,
            "decrypt_ok": bool(firecrawl_key) if firecrawl_source == "user" else None,
            "test_url_used": _default_firecrawl_test_url(db, current_user.id),
            "scrape_test_status": ("scrape_passed" if firecrawl_ts.get("ok") else _classify_provider_error(str(firecrawl_ts.get("error") or ""))) if firecrawl_ts.get("checked_at") else "configured_not_tested",
            "last_test_status": ("scrape_passed" if firecrawl_ts.get("ok") else _classify_provider_error(str(firecrawl_ts.get("error") or ""))) if firecrawl_ts.get("checked_at") else "configured_not_tested",
            "last_test_at": firecrawl_ts.get("checked_at"),
            "last_test_error": firecrawl_ts.get("error") or None,
            "last_error_classification": _classify_provider_error(str(firecrawl_ts.get("error") or "")) if firecrawl_ts.get("error") else None,
            "status": "missing_key" if firecrawl_source == "missing" else "configured_not_tested",
            "note": "Firecrawl key saved — test via POST /settings/firecrawl/debug-test" if bool(firecrawl_key) else "Add FIRECRAWL_API_KEY to enable web scraping",
        }
    except Exception as exc:
        logger.warning("providers_debug firecrawl block error: %s", exc)
        result["firecrawl"] = {"configured": False, "status": "provider_error", "error": _safe_preview(str(exc), 200)}

    # ── Qwen ──────────────────────────────────────────────────────────────────
    try:
        qwen_key, qwen_source = _resolve_provider_key(db, current_user.id, "QWEN_API_KEY", settings.QWEN_API_KEY)
        qwen_catalog_available = False
        try:
            from app.services.qwen_model_catalog import qwen_full_catalog
            cat = qwen_full_catalog()
            qwen_catalog_available = bool(cat.get("by_category"))
        except Exception:
            qwen_catalog_available = False
        result["qwen"] = {
            "configured": qwen_source != "missing",
            "key_saved": qwen_source != "missing",
            "key_source": qwen_source,
            "decrypt_ok": bool(qwen_key) if qwen_source == "user" else None,
            "catalog_available": qwen_catalog_available,
            "default_budget_text_model": settings.QWEN_MODEL or None,
            "budget_engine_available": bool(qwen_key),
            "status": "fallback_available" if bool(qwen_key) else "optional_missing",
            "test_status": "fallback_available" if bool(qwen_key) else "optional_missing",
            "note": "Qwen budget engine available" if bool(qwen_key) else "Add QWEN_API_KEY to enable Qwen fallback",
        }
    except Exception as exc:
        logger.warning("providers_debug qwen block error: %s", exc)
        result["qwen"] = {"configured": False, "status": "provider_error", "error": _safe_preview(str(exc), 200)}

    # ── HuggingFace ───────────────────────────────────────────────────────────
    try:
        hf_token, hf_source = _resolve_provider_key(db, current_user.id, "HUGGINGFACE_TOKEN", settings.HUGGINGFACE_TOKEN)
        result["huggingface"] = {
            "configured": hf_source != "missing",
            "token_saved": hf_source != "missing",
            "token_source": hf_source,
            "decrypt_ok": bool(hf_token) if hf_source == "user" else None,
            "required": False,
            "status": "fallback_available" if bool(hf_token) else "optional_missing",
            "task_status": "fallback_available" if bool(hf_token) else "optional_missing",
            "note": "HF token saved — optional fallback provider" if bool(hf_token) else "HF token optional — add HUGGINGFACE_TOKEN to enable HF tasks",
        }
    except Exception as exc:
        logger.warning("providers_debug huggingface block error: %s", exc)
        result["huggingface"] = {"configured": False, "status": "provider_error", "error": _safe_preview(str(exc), 200)}

    # ── Pixabay ───────────────────────────────────────────────────────────────
    try:
        pixabay_key, pixabay_source = _resolve_provider_key(db, current_user.id, "PIXABAY_API_KEY", settings.PIXABAY_API_KEY)
        result["pixabay"] = {
            "configured": pixabay_source != "missing",
            "key_saved": pixabay_source != "missing",
            "key_source": pixabay_source,
            "decrypt_ok": bool(pixabay_key) if pixabay_source == "user" else None,
            "status": "configured_not_tested" if bool(pixabay_key) else "missing_key",
            "image_api_status": "configured_not_tested" if bool(pixabay_key) else "missing_key",
            "video_api_status": "configured_not_tested" if bool(pixabay_key) else "missing_key",
            "note": "Pixabay key saved." if bool(pixabay_key) else "Add PIXABAY_API_KEY for stock asset search.",
        }
    except Exception as exc:
        logger.warning("providers_debug pixabay block error: %s", exc)
        result["pixabay"] = {"configured": False, "status": "provider_error", "error": _safe_preview(str(exc), 200)}

    return result


async def genx_debug_test(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    api_key, source = _resolve_provider_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    base_url = settings.GENX_BASE_URL
    model = _configured_genx_models()["effective_default_model"]
    if not api_key:
        return {
            "ok": False,
            "status": "missing",
            "effective_source": source,
            "http_status": 0,
            "base_url": base_url,
            "model": model,
            "response_shape_keys": [],
            "parsed_text_present": False,
            "sanitized_preview": "",
            "error": "GENX key is missing.",
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
            "ok": response.status_code < 400 and bool(parsed),
            "status": "ok" if response.status_code < 400 and bool(parsed) else ("provider_error" if response.status_code >= 400 else "parse_failed"),
            "effective_source": source,
            "http_status": response.status_code,
            "base_url": base_url,
            "model": model,
            "response_shape_keys": sorted(list(raw.keys())) if isinstance(raw, dict) else [],
            "parsed_text_present": bool(parsed),
            "sanitized_preview": preview,
            "error": (
                None
                if response.status_code < 400 and parsed
                else (
                    "Provider reached, but no text parsed. Check GENX_DEFAULT_MODEL."
                    if response.status_code < 400
                    else f"Provider request failed with HTTP {response.status_code}."
                )
            ),
        }
    except Exception as exc:
        logger.warning("GenX debug test failed for user %s: %s", current_user.id, type(exc).__name__)
        return {
            "ok": False,
            "status": "provider_error",
            "effective_source": source,
            "http_status": 0,
            "base_url": base_url,
            "model": model,
            "response_shape_keys": [],
            "parsed_text_present": False,
            "sanitized_preview": "",
            "error": _actionable_error_message(exc, "GenX request failed."),
        }


@router.post("/firecrawl/debug-test")
async def firecrawl_debug_test(
    test_url: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    api_key, source = _resolve_provider_key(db, current_user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY)
    endpoint = "https://api.firecrawl.dev/v2/scrape"
    if not api_key:
        return {
            "ok": False,
            "status": "missing",
            "effective_source": source,
            "endpoint": endpoint,
            "http_status": 0,
            "response_shape_keys": [],
            "parsed_content_present": False,
            "sanitized_preview": "",
            "error": "Firecrawl key is missing.",
        }
    resolved_test_url = (test_url or "").strip() or _default_firecrawl_test_url(db, current_user.id)
    if not resolved_test_url:
        return {
            "ok": False,
            "status": "no_test_url",
            "effective_source": source,
            "endpoint": endpoint,
            "http_status": 0,
            "response_shape_keys": [],
            "parsed_content_present": False,
            "sanitized_preview": "",
            "test_url_used": None,
            "error": "Add a business URL to test Firecrawl.",
        }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"url": resolved_test_url, "formats": ["markdown", "html"]},
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
        status_value = "scrape_passed" if response.status_code < 400 and bool(content) else (
            "test_url_rejected" if response.status_code == 400 else "provider_rejected_key" if response.status_code in {401, 403} else "scrape_failed"
        )
        return {
            "ok": response.status_code < 400 and bool(content),
            "status": status_value,
            "effective_source": source,
            "endpoint": endpoint,
            "test_url_used": resolved_test_url,
            "http_status": response.status_code,
            "response_shape_keys": sorted(list(raw.keys())) if isinstance(raw, dict) else [],
            "parsed_content_present": bool(content),
            "sanitized_preview": _safe_preview(content),
            "error": (
                None
                if response.status_code < 400 and bool(content)
                else (
                    "Provider reached, but no content parsed from response."
                    if response.status_code < 400
                    else f"Provider request failed with HTTP {response.status_code}."
                )
            ),
        }
    except Exception as exc:
        logger.warning("Firecrawl debug test failed for user %s: %s", current_user.id, type(exc).__name__)
        return {
            "ok": False,
            "status": "endpoint_unreachable",
            "effective_source": source,
            "endpoint": endpoint,
            "test_url_used": resolved_test_url,
            "http_status": 0,
            "response_shape_keys": [],
            "parsed_content_present": False,
            "sanitized_preview": "",
            "error": _actionable_error_message(exc, "Firecrawl request failed."),
        }


@router.get("/huggingface/tasks")
async def list_huggingface_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    token = resolve_user_api_key(db, current_user.id, "HUGGINGFACE_TOKEN", settings.HUGGINGFACE_TOKEN)
    router = HuggingFaceTaskRouter(token=token)
    return router.list_tasks()


@router.post("/huggingface/test-task")
async def test_huggingface_task(
    payload: HuggingFaceTaskTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    token = resolve_user_api_key(db, current_user.id, "HUGGINGFACE_TOKEN", settings.HUGGINGFACE_TOKEN)
    router = HuggingFaceTaskRouter(token=token)
    status_payload = router.task_status(payload.task, override_model=payload.model_override)
    if status_payload.get("status") != "available":
        return {
            "task": status_payload.get("task"),
            "status": status_payload.get("status"),
            "ok": False,
            "available": bool(status_payload.get("available")),
            "model": status_payload.get("model"),
            "endpoint_method": status_payload.get("endpoint_method"),
            "http_status": 0,
            "provider_error": None,
        }
    ok = False
    http_status = 0
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{status_payload.get('model')}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"inputs": "hello"},
            )
        http_status = response.status_code
        ok = response.status_code < 400
    except Exception:
        ok = False
        http_status = 0
    return {
        "task": status_payload.get("task"),
        "status": "available" if ok else "provider_error",
        "ok": ok,
        "available": True,
        "model": status_payload.get("model"),
        "endpoint_method": status_payload.get("endpoint_method"),
        "http_status": http_status,
        "provider_error": None if ok else "Hugging Face provider request failed.",
    }


# ==================== GenX Sub-Routes ====================

class GenXTestCapabilityRequest(BaseModel):
    category: str
    model: str | None = None
    prompt: str | None = None


class GenXModelMappingUpdate(BaseModel):
    mapping: dict[str, str]


_GENX_MODEL_MAPPING: dict[str, dict[str, str]] = {}


@router.get("/genx/models")
async def genx_models(
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.genx_router_client import GenXRouterClient
    api_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    client = GenXRouterClient(api_key=api_key)
    try:
        return await client.list_models(category=category)
    except Exception:
        return {"ok": False, "models": [], "error": "GenX models request failed."}


@router.get("/genx/capabilities")
async def genx_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.genx_router_client import GenXRouterClient
    api_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    client = GenXRouterClient(api_key=api_key)
    configured = client.configured
    return {
        "configured": configured,
        "capabilities": [
            {"category": "image", "description": "Text-to-image and image editing"},
            {"category": "video", "description": "Text-to-video, image-to-video"},
            {"category": "voice", "description": "Text-to-speech and voice cloning"},
            {"category": "avatar", "description": "Talking avatar generation"},
            {"category": "text", "description": "LLM text generation via /v1/chat/completions"},
        ] if configured else [],
        "note": "Configure GENX_API_KEY to enable GenX generation capabilities.",
    }


@router.get("/genx/model-mapping")
async def genx_model_mapping(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {"mapping": _GENX_MODEL_MAPPING.get(current_user.id, {})}


@router.put("/genx/model-mapping")
async def update_genx_model_mapping(
    payload: GenXModelMappingUpdate,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _GENX_MODEL_MAPPING[current_user.id] = payload.mapping
    return {"ok": True, "mapping": payload.mapping}


@router.post("/genx/test-capability")
async def test_genx_capability(
    payload: GenXTestCapabilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.genx_router_client import GenXRouterClient
    api_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    client = GenXRouterClient(api_key=api_key)
    try:
        return await client.test_capability(payload.category, model=payload.model, prompt=payload.prompt)
    except Exception:
        return {"ok": False, "error": "GenX capability test failed."}


@router.get("/genx/credits")
async def genx_credits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.genx_router_client import GenXRouterClient
    api_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    client = GenXRouterClient(api_key=api_key)
    try:
        return await client.get_credits()
    except Exception:
        return {"ok": False, "error": "GenX credits request failed."}


@router.get("/genx/pricing")
async def genx_pricing(
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.genx_router_client import GenXRouterClient
    api_key = resolve_user_api_key(db, current_user.id, "GENX_API_KEY", settings.GENX_API_KEY)
    client = GenXRouterClient(api_key=api_key)
    try:
        return await client.get_pricing(category=category)
    except Exception:
        return {"ok": False, "error": "GenX pricing request failed."}


# ==================== Qwen Sub-Routes ====================

class QwenTestCapabilityRequest(BaseModel):
    capability: str
    model: str | None = None
    prompt: str | None = None


@router.get("/qwen/models")
async def qwen_models(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.qwen_model_catalog import qwen_full_catalog
    return {"ok": True, "catalog": qwen_full_catalog()}


@router.get("/qwen/capabilities")
async def qwen_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.qwen_model_catalog import qwen_full_catalog
    api_key = resolve_user_api_key(db, current_user.id, "QWEN_API_KEY", settings.QWEN_API_KEY)
    catalog = qwen_full_catalog()
    return {
        "configured": bool(api_key),
        "capabilities": [
            {"category": cat, "model_count": len(models), "models": [m["model_id"] for m in models]}
            for cat, models in catalog["by_category"].items()
        ],
    }


@router.post("/qwen/test-capability")
async def test_qwen_capability(
    payload: QwenTestCapabilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.qwen_model_catalog import qwen_full_catalog
    from app.services.qwen_router import route_qwen_model
    api_key = resolve_user_api_key(db, current_user.id, "QWEN_API_KEY", settings.QWEN_API_KEY)
    if not api_key:
        return {"ok": False, "configured": False, "error": "Qwen not configured — add QWEN_API_KEY"}
    route = route_qwen_model(payload.capability, budget_mode="auto")
    return {
        "ok": True,
        "configured": True,
        "capability": payload.capability,
        "routed_model": route.get("model"),
        "note": "Live test not implemented — configure Qwen SDK for execution.",
    }
