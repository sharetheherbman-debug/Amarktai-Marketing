from __future__ import annotations

from typing import Any

from app.services.platform_catalog import normalize_platform

_BANNED = {"#Amarktai", "#AmarktaiMarketing", "#AIContent"}
_HASHTAG_LIMITS = {
    "instagram": 10,
    "pinterest": 10,
    "tiktok": 8,
    "linkedin": 4,
    "facebook": 4,
    "twitter": 3,
    "reddit": 0,
    "youtube": 5,
    "threads": 4,
    "bluesky": 3,
    "telegram": 3,
    "snapchat": 3,
}


def build_hashtag_strategy(business: dict[str, Any], platform: str) -> dict[str, Any]:
    key = normalize_platform(platform)
    limit = _HASHTAG_LIMITS.get(key, 5)
    if limit == 0:
        return {"hashtags": [], "hashtag_relevance_score": 85, "issues": ["Avoid hashtags on Reddit unless the community expects them."]}

    sources = []
    sources.extend(str(business.get("name") or "").split())
    sources.extend(str(business.get("category") or "").split())
    sources.extend(str(business.get("market_location") or "").split())
    for value in business.get("products_services") or business.get("key_features") or []:
        sources.extend(str(value).split())
    hashtags: list[str] = []
    for token in sources:
        cleaned = "".join(ch for ch in token if ch.isalnum())
        if len(cleaned) < 3:
            continue
        hashtag = f"#{cleaned}"
        if hashtag.lower() in {tag.lower() for tag in _BANNED}:
            continue
        if hashtag not in hashtags:
            hashtags.append(hashtag)
        if len(hashtags) >= limit:
            break
    score = 90 if hashtags else 55
    issues = [] if hashtags else ["Not enough business-specific keywords for strong hashtags."]
    return {"hashtags": hashtags[:limit], "hashtag_relevance_score": score, "issues": issues}
