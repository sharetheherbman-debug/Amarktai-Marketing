from __future__ import annotations

from typing import Iterable

LAUNCH_PLATFORMS: tuple[str, ...] = (
    "instagram",
    "facebook",
    "linkedin",
    "twitter",
    "tiktok",
    "youtube",
    "reddit",
    "pinterest",
)

INACTIVE_DASHBOARD_PLATFORMS: tuple[str, ...] = (
    "bluesky",
    "threads",
    "telegram",
    "snapchat",
)

_ALIASES = {
    "x": "twitter",
    "x/twitter": "twitter",
    "twitter/x": "twitter",
}


def normalize_platform(platform: str) -> str:
    value = (platform or "").strip().lower()
    return _ALIASES.get(value, value)


def launch_platforms() -> list[str]:
    return list(LAUNCH_PLATFORMS)


def is_launch_platform(platform: str) -> bool:
    return normalize_platform(platform) in LAUNCH_PLATFORMS


def filter_launch_platforms(platforms: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    filtered: list[str] = []
    for platform in platforms:
        p = normalize_platform(platform)
        if p in LAUNCH_PLATFORMS and p not in seen:
            seen.add(p)
            filtered.append(p)
    return filtered
