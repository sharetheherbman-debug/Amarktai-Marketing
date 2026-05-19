from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.social_rules import get_social_rule, resolve_platform_key, rules_snapshot

router = APIRouter()


@router.get("")
async def get_all_social_rules() -> dict:
    return {"rules": rules_snapshot()}


@router.get("/{platform}")
async def get_platform_social_rule(platform: str) -> dict:
    key = resolve_platform_key(platform)
    rule = get_social_rule(key)
    if not rule:
        raise HTTPException(status_code=404, detail=f"No social rule found for '{platform}'")
    return {
        "platform": rule.platform,
        "caption_limit": rule.caption_limit,
        "hashtag_recommended_min": rule.hashtag_recommended_min,
        "hashtag_recommended_max": rule.hashtag_recommended_max,
        "cadence": rule.cadence,
        "best_times_b2b": rule.best_times_b2b,
        "best_times_b2c": rule.best_times_b2c,
        "best_times_by_category": rule.best_times_by_category,
        "content_type_preference": rule.content_type_preference,
        "prohibited_automation": rule.prohibited_automation,
        "spam_duplicate_limits": rule.spam_duplicate_limits,
        "compliance_notes": rule.compliance_notes,
        "review_required_if": rule.review_required_if,
        "policy_notes": rule.policy_notes,
        "last_updated": rule.last_updated,
        "source_note": rule.source_note,
    }
