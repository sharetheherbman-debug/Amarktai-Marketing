from __future__ import annotations

from typing import Any

from app.services.platform_catalog import normalize_platform

# Tags that must never appear unless the business name explicitly contains "Amarktai"
# or the user explicitly requests them.
_BANNED_DEFAULT: set[str] = {
    "#amarktai",
    "#amarktaimarketing",
    "#amarktaiai",
    "#aicontent",
    "#marketingautomation",
}

# Per-platform hashtag count rules (min, max)
_HASHTAG_RULES: dict[str, dict[str, Any]] = {
    "instagram":  {"min": 8,  "max": 20, "style": "relevant_mix"},
    "pinterest":  {"min": 5,  "max": 15, "style": "keyword_rich"},
    "tiktok":     {"min": 4,  "max": 8,  "style": "category_trend"},
    "linkedin":   {"min": 3,  "max": 5,  "style": "professional"},
    "facebook":   {"min": 0,  "max": 5,  "style": "light"},
    "twitter":    {"min": 1,  "max": 3,  "style": "minimal"},
    "threads":    {"min": 1,  "max": 3,  "style": "minimal"},
    "bluesky":    {"min": 1,  "max": 3,  "style": "minimal"},
    "reddit":     {"min": 0,  "max": 0,  "style": "none"},
    "youtube":    {"min": 3,  "max": 8,  "style": "keywords"},
    "telegram":   {"min": 0,  "max": 3,  "style": "minimal"},
    "snapchat":   {"min": 0,  "max": 3,  "style": "minimal"},
}

_DEFAULT_RULE: dict[str, Any] = {"min": 2, "max": 5, "style": "general"}


def _is_amarktai_business(business: dict[str, Any]) -> bool:
    name = str(business.get("name") or "").lower()
    return "amarktai" in name


def _business_tokens(business: dict[str, Any]) -> list[str]:
    """Extract raw tokens from business fields for hashtag candidates."""
    tokens: list[str] = []
    for field in ("name", "category", "market_location"):
        tokens.extend(str(business.get(field) or "").split())
    for item in (business.get("products_services") or business.get("key_features") or []):
        tokens.extend(str(item).split())
    offer = business.get("offer") or business.get("current_offer") or ""
    if offer:
        tokens.extend(str(offer).split())
    return tokens


def _clean_token(token: str) -> str:
    return "".join(ch for ch in token if ch.isalnum())


def build_hashtag_strategy(
    business: dict[str, Any],
    platform: str,
    *,
    allow_amarktai: bool = False,
    extra_tokens: list[str] | None = None,
) -> dict[str, Any]:
    """Build a platform-appropriate hashtag set grounded in the business profile.

    Args:
        business: Business profile dict (name, category, market_location, etc.)
        platform: Target platform slug.
        allow_amarktai: Allow Amarktai-brand tags only when the business name
            contains "Amarktai" or the caller explicitly opts in.
        extra_tokens: Additional keyword tokens from offer/objective overrides.

    Returns:
        dict with keys: hashtags, hashtag_relevance_score, issues, platform, limit
    """
    key = normalize_platform(platform)
    rule = _HASHTAG_RULES.get(key, _DEFAULT_RULE)
    max_tags = rule["max"]
    issues: list[str] = []

    # Reddit and platforms with max=0 get no hashtags
    if max_tags == 0:
        return {
            "hashtags": [],
            "hashtag_relevance_score": 85,
            "issues": ["Hashtags are not standard on this platform — omitted."],
            "platform": key,
            "limit": 0,
        }

    # Determine if Amarktai brand tags are allowed
    amarktai_ok = allow_amarktai or _is_amarktai_business(business)

    # Collect candidate tokens
    raw_tokens = _business_tokens(business)
    if extra_tokens:
        raw_tokens.extend(extra_tokens)

    # Build candidate hashtags
    seen_lower: set[str] = set()
    hashtags: list[str] = []
    banned_found: list[str] = []

    for token in raw_tokens:
        cleaned = _clean_token(token)
        if len(cleaned) < 3:
            continue
        tag = f"#{cleaned}"
        tag_lower = tag.lower()
        if tag_lower in seen_lower:
            continue
        seen_lower.add(tag_lower)
        if tag_lower in _BANNED_DEFAULT:
            if not amarktai_ok:
                banned_found.append(tag)
                continue
        hashtags.append(tag)
        if len(hashtags) >= max_tags:
            break

    if banned_found:
        issues.append(f"Removed brand/generic tags not relevant to this business: {', '.join(banned_found)}")

    if not hashtags:
        issues.append("Not enough business-specific keywords for strong hashtags. Add products/services to the business profile.")

    # Score based on how business-grounded the tags are
    if len(hashtags) >= rule.get("min", 1):
        score = 90
    elif hashtags:
        score = 70
    else:
        score = 40

    return {
        "hashtags": hashtags[:max_tags],
        "hashtag_relevance_score": score,
        "issues": issues,
        "platform": key,
        "limit": max_tags,
    }


def validate_hashtags(
    hashtags: list[str],
    business: dict[str, Any],
    *,
    allow_amarktai: bool = False,
) -> dict[str, Any]:
    """Check an existing hashtag list for banned/irrelevant tags.

    Returns a dict with: ok, removed, issues.
    """
    amarktai_ok = allow_amarktai or _is_amarktai_business(business)
    cleaned: list[str] = []
    removed: list[str] = []
    issues: list[str] = []

    for tag in hashtags:
        if tag.lower().lstrip("#") == "":
            continue
        tag_lower = tag.lower()
        if tag_lower in _BANNED_DEFAULT and not amarktai_ok:
            removed.append(tag)
        else:
            cleaned.append(tag)

    if removed:
        issues.append(f"Removed brand/generic tags: {', '.join(removed)}")

    return {
        "ok": not removed,
        "hashtags": cleaned,
        "removed": removed,
        "issues": issues,
        "needs_review_hashtags": bool(removed),
    }
