from __future__ import annotations

from typing import Any, Iterable

from app.core.config import settings

PLATFORM_ORDER: tuple[str, ...] = (
    "instagram",
    "facebook",
    "linkedin",
    "twitter",
    "tiktok",
    "youtube",
    "reddit",
    "pinterest",
    "threads",
    "bluesky",
    "telegram",
    "snapchat",
)

LAUNCH_PLATFORMS: tuple[str, ...] = PLATFORM_ORDER

_ALIASES = {
    "x": "twitter",
    "x/twitter": "twitter",
    "twitter/x": "twitter",
}

_PLATFORM_LABELS = {
    "instagram": "Instagram",
    "facebook": "Facebook",
    "linkedin": "LinkedIn",
    "twitter": "X / Twitter",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "reddit": "Reddit",
    "pinterest": "Pinterest",
    "threads": "Threads",
    "bluesky": "Bluesky",
    "telegram": "Telegram",
    "snapchat": "Snapchat",
}

_POSTING_IMPLEMENTED = {
    "instagram": True,
    "facebook": True,
    "linkedin": True,
    "twitter": False,
    "tiktok": False,
    "youtube": False,
    "reddit": True,
    "pinterest": True,
    "threads": False,
    "bluesky": False,
    "telegram": False,
    "snapchat": False,
}


def normalize_platform(platform: str) -> str:
    value = (platform or "").strip().lower()
    return _ALIASES.get(value, value)


def _oauth_configured(platform: str) -> bool:
    p = normalize_platform(platform)
    if p in {"facebook", "instagram", "threads"}:
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
    if p == "bluesky":
        return bool(settings.BLUESKY_CLIENT_ID)
    if p == "telegram":
        return bool(settings.TELEGRAM_BOT_TOKEN)
    if p == "snapchat":
        return bool(settings.SNAPCHAT_CLIENT_ID and settings.SNAPCHAT_CLIENT_SECRET)
    return False


def platform_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for platform in PLATFORM_ORDER:
        oauth_configured = _oauth_configured(platform)
        posting_supported = _POSTING_IMPLEMENTED.get(platform, False)
        if posting_supported and oauth_configured:
            status_label = "Posting supported"
            user_message = "Content generation is available. Connect OAuth to enable posting."
        elif posting_supported and not oauth_configured:
            status_label = "OAuth not configured"
            user_message = "Content generation is available. Posting can be enabled after OAuth app configuration."
        else:
            status_label = "Generation only"
            user_message = "Content generation is available. Posting is not configured for this platform yet."
        catalog.append(
            {
                "id": platform,
                "key": platform,
                "label": _PLATFORM_LABELS[platform],
                "aliases": [alias for alias, target in _ALIASES.items() if target == platform],
                "content_generation_available": True,
                "oauth_supported": True,
                "oauth_configured": oauth_configured,
                "posting_supported": posting_supported,
                "analytics_supported": platform in {
                    "instagram", "facebook", "linkedin", "twitter", "tiktok", "youtube", "reddit", "pinterest"
                },
                "status_label": status_label,
                "user_message": user_message,
            }
        )
    return catalog


def platform_map() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in platform_catalog()}


def launch_platforms() -> list[str]:
    return list(PLATFORM_ORDER)


def all_platforms() -> list[str]:
    return list(PLATFORM_ORDER)


def platform_label(platform: str) -> str:
    return _PLATFORM_LABELS.get(normalize_platform(platform), normalize_platform(platform).title())


def is_launch_platform(platform: str) -> bool:
    return normalize_platform(platform) in PLATFORM_ORDER


def filter_launch_platforms(platforms: Iterable[str] | None) -> list[str]:
    if not platforms:
        return list(PLATFORM_ORDER)
    seen: set[str] = set()
    filtered: list[str] = []
    for platform in platforms:
        p = normalize_platform(platform)
        if p in PLATFORM_ORDER and p not in seen:
            seen.add(p)
            filtered.append(p)
    return filtered
