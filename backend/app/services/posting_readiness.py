from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user_api_key import UserIntegration
from app.services.platform_catalog import LAUNCH_PLATFORMS, normalize_platform

PLATFORM_KEYS = list(LAUNCH_PLATFORMS)

POSTING_IMPLEMENTED = {
    "facebook": True,
    "instagram": True,
    "linkedin": True,
    "twitter": False,
    "tiktok": False,
    "youtube": False,
    "reddit": True,
    "pinterest": True,
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
}


def _oauth_configured(platform: str) -> bool:
    p = normalize_platform(platform)
    if p == "facebook":
        return bool(settings.META_APP_ID and settings.META_APP_SECRET)
    if p == "instagram":
        return bool(settings.META_APP_ID and settings.META_APP_SECRET)
    if p == "linkedin":
        return bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET)
    if p == "twitter":
        return bool(settings.TWITTER_CLIENT_ID and settings.TWITTER_CLIENT_SECRET)
    if p == "tiktok":
        return bool(settings.TIKTOK_CLIENT_KEY and settings.TIKTOK_CLIENT_SECRET)
    if p == "youtube":
        return bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET)
    if p == "reddit":
        return bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET)
    if p == "pinterest":
        return bool(settings.PINTEREST_CLIENT_ID and settings.PINTEREST_CLIENT_SECRET)
    return False


def _parse_scopes(scopes_value: str | None) -> set[str]:
    if not scopes_value:
        return set()
    tokens: list[str] = []
    for chunk in scopes_value.replace(",", " ").split():
        value = chunk.strip()
        if value:
            tokens.append(value)
    return set(tokens)


def platform_posting_state(db: Session, user_id: str, platform: str) -> dict[str, Any]:
    p = normalize_platform(platform)
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.platform == p,
    ).first()

    oauth_configured = _oauth_configured(p)
    user_connected = bool(integration and integration.is_connected)
    has_access_token = False
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
    scopes_ok = bool(required_scopes) and required_scopes.issubset(scopes_available)
    posting_supported = POSTING_IMPLEMENTED.get(p, False)
    analytics_supported = p in {"facebook", "instagram", "linkedin", "twitter", "tiktok", "youtube", "reddit", "pinterest"}
    rate_limit_known = p in {"facebook", "instagram", "linkedin", "twitter", "tiktok", "youtube", "reddit", "pinterest"}

    missing: list[str] = []
    if not oauth_configured:
        missing.append("oauth_config")
    if not user_connected:
        missing.append("user_connection")
    if not token_valid:
        missing.append("token")
    if not scopes_ok:
        missing.append("scopes")
    if not posting_supported:
        missing.append("posting_not_implemented")
    if not payload_ok:
        missing.append("platform_target")

    can_post_now = oauth_configured and user_connected and token_valid and scopes_ok and posting_supported and payload_ok
    status = (
        "Ready to post"
        if can_post_now
        else ("Not supported yet" if not posting_supported else ("Needs connection" if not user_connected else ("Needs token refresh" if not token_valid else "Needs connection")))
    )

    return {
        "platform": p,
        "generate_ready": True,
        "oauth_configured": oauth_configured,
        "user_connected": user_connected,
        "token_valid": token_valid,
        "scopes_ok": scopes_ok,
        "posting_supported": posting_supported,
        "posting_ready": can_post_now,
        "analytics_supported": analytics_supported,
        "rate_limit_known": rate_limit_known,
        "can_post_now": can_post_now,
        "status": (
            "posting_ready"
            if can_post_now
            else (
                "oauth_not_configured" if not oauth_configured
                else ("oauth_configured" if oauth_configured and not user_connected else ("user_connected" if user_connected and not posting_supported else "posting_not_implemented"))
            )
        ),
        "missing": missing,
        "required_scopes": sorted(required_scopes),
        "granted_scopes": sorted(scopes_available),
        "platform_target_ok": payload_ok,
        "required_platform_fields": sorted(payload_fields),
        "ui_status": status,
    }


def publishing_readiness(db: Session, user_id: str) -> dict[str, Any]:
    states = {p: platform_posting_state(db, user_id, p) for p in PLATFORM_KEYS}
    return {
        "platforms": states,
        "ready_platforms": [k for k, v in states.items() if v["can_post_now"]],
        "blocked_platforms": [k for k, v in states.items() if not v["can_post_now"]],
    }
