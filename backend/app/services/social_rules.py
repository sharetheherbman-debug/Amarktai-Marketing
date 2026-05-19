"""Data-driven social platform guidance and guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SocialRule:
    platform: str
    caption_limit: int
    hashtag_recommended_min: int
    hashtag_recommended_max: int
    cadence: str
    best_times_b2b: list[str]
    best_times_b2c: list[str]
    best_times_by_category: dict[str, list[str]]
    content_type_preference: list[str]
    prohibited_automation: list[str]
    spam_duplicate_limits: list[str]
    compliance_notes: list[str]
    review_required_if: list[str]
    policy_notes: list[str]
    last_updated: str
    source_note: str


SOCIAL_RULES: dict[str, SocialRule] = {
    "facebook": SocialRule(
        platform="facebook",
        caption_limit=63206,
        hashtag_recommended_min=2,
        hashtag_recommended_max=5,
        cadence="3-7 posts/week",
        best_times_b2b=["Tue 09:00", "Wed 11:00", "Thu 13:00"],
        best_times_b2c=["Mon 12:00", "Wed 15:00", "Fri 18:00"],
        best_times_by_category={"saas_b2b": ["Tue 09:00", "Wed 11:00"], "ecommerce_b2c": ["Wed 15:00", "Fri 18:00"]},
        content_type_preference=["value carousel", "case study post", "short native video"],
        prohibited_automation=["auto-join groups", "repetitive spam comments", "engagement bait loops"],
        spam_duplicate_limits=["Avoid posting near-duplicate copy in <24h", "Do not mass-repeat identical links/captions"],
        compliance_notes=["Avoid deceptive claims", "Respect ad/promo disclosure requirements"],
        review_required_if=["medical/financial/legal claims", "before/after outcome promises"],
        policy_notes=["Follow Meta Community Standards and Page policies", "Do not automate deceptive engagement behavior"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "instagram": SocialRule(
        platform="instagram",
        caption_limit=2200,
        hashtag_recommended_min=3,
        hashtag_recommended_max=10,
        cadence="4-10 posts/week",
        best_times_b2b=["Tue 11:00", "Wed 10:00", "Thu 12:00"],
        best_times_b2c=["Mon 18:00", "Wed 19:00", "Sat 11:00"],
        best_times_by_category={"saas_b2b": ["Tue 11:00", "Thu 12:00"], "creator_b2c": ["Wed 19:00", "Sat 11:00"]},
        content_type_preference=["reels", "carousel", "ugc-style short video"],
        prohibited_automation=["follow/unfollow farms", "mass duplicate hashtags", "spam DMs"],
        spam_duplicate_limits=["Avoid repeated hashtag blocks in back-to-back posts", "Rotate captions and media variants"],
        compliance_notes=["Use clear CTA", "Keep hashtags relevant"],
        review_required_if=["sensitive categories", "sweepstakes/giveaway promotions"],
        policy_notes=["Follow Instagram Terms and branded content disclosures", "Avoid aggressive bot-like growth behavior"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "linkedin": SocialRule(
        platform="linkedin",
        caption_limit=3000,
        hashtag_recommended_min=2,
        hashtag_recommended_max=5,
        cadence="2-5 posts/week",
        best_times_b2b=["Tue 08:00", "Wed 09:00", "Thu 08:30"],
        best_times_b2c=["Mon 10:00", "Wed 12:00", "Fri 09:00"],
        best_times_by_category={"saas_b2b": ["Tue 08:00", "Wed 09:00"], "services_b2c": ["Mon 10:00", "Wed 12:00"]},
        content_type_preference=["thought leadership", "industry analysis", "customer outcome stories"],
        prohibited_automation=["connection spam", "auto-comment pods", "mass duplicate outreach"],
        spam_duplicate_limits=["Limit repetitive outbound templates", "Avoid duplicate posts in short intervals"],
        compliance_notes=["Professional tone", "Prioritize value-first insight"],
        review_required_if=["performance guarantees", "regulated industry messaging"],
        policy_notes=["Follow LinkedIn Professional Community Policies", "Avoid automated engagement manipulation"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "twitter": SocialRule(
        platform="twitter",
        caption_limit=280,
        hashtag_recommended_min=1,
        hashtag_recommended_max=3,
        cadence="1-5 posts/day",
        best_times_b2b=["Tue 10:00", "Wed 12:00", "Thu 09:00"],
        best_times_b2c=["Mon 13:00", "Wed 18:00", "Fri 15:00"],
        best_times_by_category={"saas_b2b": ["Tue 10:00", "Thu 09:00"], "consumer_b2c": ["Wed 18:00", "Fri 15:00"]},
        content_type_preference=["short text thread", "timely commentary", "visual-with-caption post"],
        prohibited_automation=["duplicate tweet floods", "reply spam bots", "misleading trend hijacks"],
        spam_duplicate_limits=["No high-frequency duplicate tweets", "Throttle repetitive replies and mentions"],
        compliance_notes=["Stay concise", "Avoid repetitive hashtag stuffing"],
        review_required_if=["breaking-news claims", "market/financial advice"],
        policy_notes=["Follow X automation and spam policies", "Avoid synthetic or coordinated manipulative behavior"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "x": SocialRule(
        platform="x",
        caption_limit=280,
        hashtag_recommended_min=1,
        hashtag_recommended_max=3,
        cadence="1-5 posts/day",
        best_times_b2b=["Tue 10:00", "Wed 12:00", "Thu 09:00"],
        best_times_b2c=["Mon 13:00", "Wed 18:00", "Fri 15:00"],
        best_times_by_category={"saas_b2b": ["Tue 10:00", "Thu 09:00"], "consumer_b2c": ["Wed 18:00", "Fri 15:00"]},
        content_type_preference=["short text thread", "timely commentary", "visual-with-caption post"],
        prohibited_automation=["duplicate tweet floods", "reply spam bots", "misleading trend hijacks"],
        spam_duplicate_limits=["No high-frequency duplicate tweets", "Throttle repetitive replies and mentions"],
        compliance_notes=["Stay concise", "Avoid repetitive hashtag stuffing"],
        review_required_if=["breaking-news claims", "market/financial advice"],
        policy_notes=["Follow X automation and spam policies", "Avoid synthetic or coordinated manipulative behavior"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "tiktok": SocialRule(
        platform="tiktok",
        caption_limit=2200,
        hashtag_recommended_min=3,
        hashtag_recommended_max=8,
        cadence="4-14 posts/week",
        best_times_b2b=["Tue 12:00", "Wed 13:00", "Thu 11:00"],
        best_times_b2c=["Mon 19:00", "Thu 20:00", "Sat 10:00"],
        best_times_by_category={"saas_b2b": ["Tue 12:00", "Wed 13:00"], "creator_b2c": ["Thu 20:00", "Sat 10:00"]},
        content_type_preference=["short-form trend video", "educational quick tips", "before/after montage"],
        prohibited_automation=["bot engagement loops", "fake engagement exchanges", "mass duplicate captions"],
        spam_duplicate_limits=["Avoid serial reposting the same creative", "Limit repetitive trending hashtag abuse"],
        compliance_notes=["Hook in first line", "Clear CTA without spam"],
        review_required_if=["health claims", "financial promises", "safety-sensitive content"],
        policy_notes=["Follow TikTok Community Guidelines and branded content requirements", "Avoid fake engagement tactics"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "youtube": SocialRule(
        platform="youtube",
        caption_limit=5000,
        hashtag_recommended_min=3,
        hashtag_recommended_max=8,
        cadence="2-6 videos/week",
        best_times_b2b=["Tue 11:00", "Thu 12:00", "Fri 11:00"],
        best_times_b2c=["Wed 18:00", "Fri 19:00", "Sun 16:00"],
        best_times_by_category={"saas_b2b": ["Tue 11:00", "Thu 12:00"], "creator_b2c": ["Fri 19:00", "Sun 16:00"]},
        content_type_preference=["short explainer video", "how-to walkthrough", "community Q&A clip"],
        prohibited_automation=["misleading metadata spam", "duplicate uploads for manipulation"],
        spam_duplicate_limits=["Avoid duplicate uploads with minor edits", "Do not spam title/description keywords"],
        compliance_notes=["Description should summarize value", "Use compliant disclosure for sponsorships"],
        review_required_if=["medical/finance/children topics", "copyright-sensitive media"],
        policy_notes=["Follow YouTube spam/deceptive practices and copyright policies", "Use original or licensed media only"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
    "reddit": SocialRule(
        platform="reddit",
        caption_limit=40000,
        hashtag_recommended_min=0,
        hashtag_recommended_max=0,
        cadence="3-10 posts/week (subreddit-dependent)",
        best_times_b2b=["Tue 09:00", "Wed 10:00", "Thu 09:00"],
        best_times_b2c=["Mon 20:00", "Wed 21:00", "Sat 11:00"],
        best_times_by_category={"saas_b2b": ["Tue 09:00", "Wed 10:00"], "community_b2c": ["Wed 21:00", "Sat 11:00"]},
        content_type_preference=["discussion prompt", "AMA-style content", "value-first educational post"],
        prohibited_automation=["cross-post spam", "vote manipulation", "subreddit rule bypassing"],
        spam_duplicate_limits=["Do not repost identical submissions across many subreddits", "Respect subreddit posting frequency limits"],
        compliance_notes=["Subreddit-first tone", "Value-first and non-salesy"],
        review_required_if=["self-promotion", "sensitive topics"],
        policy_notes=["Follow Reddit content policy and subreddit-specific rules", "No vote manipulation or brigading"],
        last_updated="2026-05-19",
        source_note="Conservative, publicly known guidance only; no private algorithm access.",
    ),
}


def resolve_platform_key(platform: str) -> str:
    p = (platform or "").strip().lower()
    aliases = {
        "twitter/x": "twitter",
        "x/twitter": "twitter",
        "reels": "instagram",
        "shorts": "youtube",
    }
    return aliases.get(p, p)


def get_social_rule(platform: str) -> SocialRule | None:
    return SOCIAL_RULES.get(resolve_platform_key(platform))


def as_prompt_guidance(platform: str, customer_type: str = "b2c") -> str:
    rule = get_social_rule(platform)
    if not rule:
        return "Use clear, non-spammy language, concise CTA, and platform-native tone."
    best_times = rule.best_times_b2b if customer_type.lower() == "b2b" else rule.best_times_b2c
    return (
        f"Platform constraints: caption<= {rule.caption_limit} chars; "
        f"hashtags {rule.hashtag_recommended_min}-{rule.hashtag_recommended_max}. "
        f"Cadence guidance: {rule.cadence}. Suggested times: {', '.join(best_times)}. "
        f"Preferred formats: {', '.join(rule.content_type_preference)}. "
        f"Avoid: {', '.join(rule.prohibited_automation)}. "
        f"Spam limits: {', '.join(rule.spam_duplicate_limits)}. "
        f"Compliance: {', '.join(rule.compliance_notes)}. "
        f"Require human review for: {', '.join(rule.review_required_if)}. "
        f"Policy notes: {', '.join(rule.policy_notes)}. "
        f"Source note: {rule.source_note}"
    )


def rules_snapshot() -> dict[str, Any]:
    return {
        key: {
            "caption_limit": value.caption_limit,
            "hashtag_recommended_min": value.hashtag_recommended_min,
            "hashtag_recommended_max": value.hashtag_recommended_max,
            "cadence": value.cadence,
            "best_times_b2b": value.best_times_b2b,
            "best_times_b2c": value.best_times_b2c,
            "best_times_by_category": value.best_times_by_category,
            "content_type_preference": value.content_type_preference,
            "prohibited_automation": value.prohibited_automation,
            "spam_duplicate_limits": value.spam_duplicate_limits,
            "compliance_notes": value.compliance_notes,
            "review_required_if": value.review_required_if,
            "policy_notes": value.policy_notes,
            "last_updated": value.last_updated,
            "source_note": value.source_note,
        }
        for key, value in SOCIAL_RULES.items()
    }
