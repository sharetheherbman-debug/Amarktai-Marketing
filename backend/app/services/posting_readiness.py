from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.user_api_key import UserIntegration
from app.services.platform_catalog import all_platforms, normalize_platform, platform_map

PLATFORM_KEYS = list(all_platforms())

POSTING_IMPLEMENTED = {
    key: bool((platform_map().get(key) or {}).get("posting_supported", False))
    for key in PLATFORM_KEYS
}

REQUIRED_SCOPES = {
    "facebook": {"pages_manage_posts"},
    "instagram": {"instagram_content_publish"},
    "linkedin": {"w_member_social"},
    "twitter": {"tweet.write"},
    "tiktok": {"video.publish"},
    "youtube": {"https://www.googleapis.com/auth/youtube.upload"},
    "reddit": {"submit"},
    "pinterest": {"pins:write"},
    "threads": {"threads_content_publish"},
    "bluesky": {"atproto"},
    "telegram": {"messages"},
    "snapchat": {"snapchat-marketing-api"},
}

REQUIRED_PLATFORM_FIELDS = {
    "facebook": {"page_id"},
    "instagram": {"ig_user_id"},
    "linkedin": {"person_urn"},
    "twitter": set(),
    "tiktok": set(),
    "youtube": set(),
    "reddit": {"subreddit"},
    "pinterest": {"board_id"},
    "threads": set(),
    "bluesky": set(),
    "telegram": {"channel_id"},
    "snapchat": set(),
}


def _parse_scopes(scopes_value: str | None) -> set[str]:
    if not scopes_value:
        return set()
    tokens: list[str] = []
    for chunk in scopes_value.replace(",", " ").split():
        value = chunk.strip()
        if value:
            tokens.append(value)
    return set(tokens)


def _token_decrypt_ok(integration: UserIntegration | None) -> bool:
    if not integration or not integration.encrypted_access_token:
        return False
    try:
        token = integration.get_access_token()
        return bool(token)
    except Exception:
        return False


def platform_posting_state(db: Session, user_id: str, platform: str) -> dict[str, Any]:
    p = normalize_platform(platform)
    catalog_entry = platform_map().get(p, {})
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.platform == p,
    ).first()

    oauth_configured = bool(catalog_entry.get("oauth_configured", False))
    marked_connected = bool(integration and integration.is_connected)
    has_access_token = False
    token_decrypt_ok = _token_decrypt_ok(integration)
    token_valid = False
    scopes_available: set[str] = set()

    if integration:
        has_access_token = bool(integration.encrypted_access_token)
        scopes_available = _parse_scopes(integration.scopes)
        if integration.token_expires_at:
            expiry = integration.token_expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            token_valid = has_access_token and expiry > datetime.now(timezone.utc)
        else:
            token_valid = has_access_token

    payload_fields = REQUIRED_PLATFORM_FIELDS.get(p, set())
    payload_data: dict[str, Any] = {}
    if integration and integration.platform_data:
        try:
            payload_data = json.loads(integration.platform_data)
            if not isinstance(payload_data, dict):
                payload_data = {}
        except Exception:
            payload_data = {}
    payload_ok = all(bool(payload_data.get(k)) for k in payload_fields)

    required_scopes = REQUIRED_SCOPES.get(p, set())
    scopes_ok = required_scopes.issubset(scopes_available) if required_scopes else True
    posting_supported = POSTING_IMPLEMENTED.get(p, False)
    analytics_supported = bool(catalog_entry.get("analytics_supported", False))
    rate_limit_known = analytics_supported

    user_connected = bool(
        marked_connected
        and has_access_token
        and token_decrypt_ok
        and token_valid
        and scopes_ok
        and payload_ok
    )

    missing: list[str] = []
    if not oauth_configured:
        missing.append("oauth_config")
    if not marked_connected:
        missing.append("user_connection")
    if not has_access_token:
        missing.append("token_missing")
    if has_access_token and not token_decrypt_ok:
        missing.append("token_decrypt_failed")
    if not token_valid:
        missing.append("token_invalid_or_expired")
    if not scopes_ok:
        missing.append("scopes")
    if not posting_supported:
        missing.append("posting_not_implemented")
    if not payload_ok:
        missing.append("platform_target")

    can_post_now = oauth_configured and user_connected and posting_supported
    if not oauth_configured:
        status = "oauth_app_not_configured"
        action_label = "Configure OAuth app"
    elif not posting_supported:
        status = "generation_only"
        action_label = "Generation only"
    elif not user_connected:
        status = "needs_connection"
        action_label = "Connect account"
    else:
        status = "ready_to_post"
        action_label = "Manage connection"

    return {
        "platform": p,
        "generate_ready": True,
        "oauth_configured": oauth_configured,
        "user_connected": user_connected,
        "marked_connected": marked_connected,
        "token_valid": token_valid,
        "token_decrypt_ok": token_decrypt_ok,
        "has_access_token": has_access_token,
        "scopes_ok": scopes_ok,
        "posting_supported": posting_supported,
        "posting_ready": can_post_now,
        "analytics_supported": analytics_supported,
        "rate_limit_known": rate_limit_known,
        "can_post_now": can_post_now,
        "status": status,
        "missing": missing,
        "required_scopes": sorted(required_scopes),
        "granted_scopes": sorted(scopes_available),
        "platform_target_ok": payload_ok,
        "required_platform_fields": sorted(payload_fields),
        "ui_status": status,
        "status_label": catalog_entry.get("status_label", status),
        "action_label": action_label,
        "user_message": catalog_entry.get("user_message", "Content generation is available."),
    }


def publishing_readiness(db: Session, user_id: str) -> dict[str, Any]:
    states = {p: platform_posting_state(db, user_id, p) for p in PLATFORM_KEYS}
    return {
        "platforms": states,
        "ready_platforms": [k for k, v in states.items() if v["can_post_now"]],
        "blocked_platforms": [k for k, v in states.items() if not v["can_post_now"]],
    }
