from __future__ import annotations

from typing import Any

from app.services.social_rules import rules_snapshot, resolve_platform_key


PLATFORM_STYLE = {
    "tiktok": {"focus": "video-first", "hook_style": "fast hook in first 2 seconds"},
    "youtube": {"focus": "video-first", "hook_style": "title + thumbnail authority hook"},
    "instagram": {"focus": "visual-first", "hook_style": "visual storytelling hook"},
    "pinterest": {"focus": "visual-first", "hook_style": "keyword-rich inspiration hook"},
    "linkedin": {"focus": "professional/authority-first", "hook_style": "insight-led authority hook"},
    "reddit": {"focus": "discussion-first, low promotion", "hook_style": "community-first discussion prompt"},
    "twitter": {"focus": "concise/thread-first", "hook_style": "short curiosity hook"},
    "facebook": {"focus": "community/CTA-first", "hook_style": "community value + CTA"},
}


def get_platform_intelligence(platform: str | None = None) -> dict[str, Any]:
    rules = rules_snapshot()
    if platform:
        key = resolve_platform_key(platform)
        rule = rules.get(key)
        if not rule:
            return {"platform": key, "status": "not_found"}
        return {"platform": key, **_merge_rule(rule, key)}
    return {"platforms": {key: _merge_rule(rule, key) for key, rule in rules.items()}}


def review_content(*, platform: str, content: str, business_type: str | None = None) -> dict[str, Any]:
    key = resolve_platform_key(platform)
    rules = rules_snapshot().get(key, {})
    style = PLATFORM_STYLE.get(key, {})
    text = (content or "").lower()
    risks = []
    terms_warnings = []
    if "guaranteed" in text or "guarantee" in text:
        risks.append("Avoid guaranteed outcome claims.")
        terms_warnings.append("Do not promise guaranteed followers/customers.")
    if key == "reddit" and "#" in (content or ""):
        risks.append("Reddit posts should avoid spammy hashtag style.")
    platform_fit_score = 82
    if risks:
        platform_fit_score = 62
    return {
        "platform": key,
        "platform_fit_score": platform_fit_score,
        "risks": risks,
        "improvements": [
            "Use realistic wording such as optimize for growth and increase likelihood.",
            f"Align with {style.get('focus', 'platform-native')} format.",
        ],
        "terms_policy_warnings": terms_warnings,
        "algorithm_fit_suggestions": [f"Prefer {style.get('focus', 'platform-native')} content format."],
        "customer_conversion_suggestions": ["Use a clear CTA tied to business value proposition."],
        "follower_growth_suggestions": ["Use repeatable hooks, consistent cadence, and audience-specific value."],
        "business_type": business_type or "general",
        "rules_reference": rules,
    }


def _merge_rule(rule: dict[str, Any], key: str) -> dict[str, Any]:
    style = PLATFORM_STYLE.get(key, {})
    return {
        "content_formats_best": rule.get("content_type_preference", []),
        "recommended_cadence": rule.get("cadence"),
        "hook_style": style.get("hook_style"),
        "caption_length_guidance": f"<= {rule.get('caption_limit', 500)} chars",
        "hashtag_guidance": f"{rule.get('hashtag_recommended_min', 0)}-{rule.get('hashtag_recommended_max', 0)} recommended",
        "media_requirements": style.get("focus", "platform-native"),
        "compliance_guardrails": rule.get("compliance_notes", []),
        "terms_guardrails": rule.get("policy_notes", []),
        "spam_automation_risk_rules": rule.get("prohibited_automation", []),
        "posting_time_windows": rule.get("best_times_by_category", {}),
        "engagement_tactics": ["Prompt replies with clear questions.", "Use native format conventions."],
        "follower_growth_tactics": ["Consistency over volume.", "Iterate hooks by performance."],
        "customer_acquisition_tactics": ["Pair value claim with proof and CTA.", "Use offer-context alignment by platform."],
        "prohibited_claims_actions": ["Guaranteed followers/customers", "Unrealistic income/health/legal promises"],
        "human_review_triggers": rule.get("review_required_if", []),
    }
