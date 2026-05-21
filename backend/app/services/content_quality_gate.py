from __future__ import annotations

from typing import Any


def evaluate_quality_gate(
    *,
    business_grounding_score: int,
    hashtag_relevance_score: int,
    creative_relevance_score: int | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    if business_grounding_score < 70:
        issues.append("Business grounding below threshold.")
    if hashtag_relevance_score < 70:
        issues.append("Hashtag relevance below threshold.")
    if creative_relevance_score is not None and creative_relevance_score < 70:
        issues.append("Creative relevance below threshold.")
    return {
        "ready": not issues,
        "needs_review": bool(issues),
        "issues": issues,
        "status": "ready" if not issues else "needs_review",
    }


# ── Structured output builders ────────────────────────────────────────────────

def build_ad_campaign_structure(
    *,
    business: dict[str, Any],
    objective: str = "",
    offer: str = "",
    audience: str = "",
    platform: str = "",
    has_media_provider: bool = False,
) -> dict[str, Any]:
    """Return a structured Ad Campaign output skeleton.

    Useful even without media providers — creative brief and copy plan are
    always populated; media fields indicate availability.
    """
    biz_name = business.get("name") or "your business"
    category = business.get("category") or "business"
    return {
        "output_type": "ad_campaign",
        "campaign_concept": f"{objective or 'Awareness'} campaign for {biz_name} ({category})",
        "hooks": [
            f"Hook 1: Lead with the problem your {category} solves",
            f"Hook 2: Show the result your customers get",
            f"Hook 3: Make the offer irresistible — {offer or 'limited time offer'}",
        ],
        "primary_text": f"[Generated primary ad copy for {biz_name} targeting {audience or 'ideal audience'}]",
        "headline": f"[Generated headline — {objective or 'compelling benefit'}]",
        "cta": "Learn More" if not objective else _cta_for_objective(objective),
        "creative_brief": (
            f"Visual style: {category} professional. "
            f"Show {offer or 'key product/service'} in use. "
            f"Platform: {platform or 'multi-platform'}."
        ),
        "placement_suggestion": _placement_for_platform(platform),
        "asset_recommendation": (
            "Configured: image/video generation available." if has_media_provider
            else "No media provider configured — use Pixabay stock or upload your own assets."
        ),
        "schedule_suggestion": "Best time: Tuesday–Thursday 9 am–2 pm local time.",
        "media_ready": has_media_provider,
    }


def build_short_video_structure(
    *,
    business: dict[str, Any],
    offer: str = "",
    platform: str = "tiktok",
    has_media_provider: bool = False,
) -> dict[str, Any]:
    biz_name = business.get("name") or "your business"
    return {
        "output_type": "short_video",
        "first_3_second_hook": f"[Hook — grab attention in the first 3 seconds for {biz_name}]",
        "scene_by_scene_script": [
            {"scene": 1, "duration_sec": 3, "action": "Hook — bold statement or question", "caption": "[Caption text]"},
            {"scene": 2, "duration_sec": 5, "action": "Problem or context — why it matters", "caption": "[Caption text]"},
            {"scene": 3, "duration_sec": 7, "action": f"Solution — {offer or 'your offer'}", "caption": "[Caption text]"},
            {"scene": 4, "duration_sec": 5, "action": "Proof or result", "caption": "[Caption text]"},
            {"scene": 5, "duration_sec": 5, "action": "CTA — clear next step", "caption": "[Caption text]"},
        ],
        "shot_list": ["Wide establishing shot", "Close-up product/service", "Reaction / result shot", "CTA card"],
        "on_screen_captions": "[Auto-generated captions from script — add to editing tool]",
        "voiceover": "[Voiceover script matched to scene timing]",
        "music_sound_suggestion": "Trending upbeat track / platform-matched sound",
        "asset_search_plan": f"Pixabay search: '{business.get('category', 'business')} {offer}'",
        "thumbnail_idea": "[Bold text overlay on high-contrast frame]",
        "cta": _cta_for_objective("engagement"),
        "duration_recommendation": f"{'15-30 sec' if platform in ('tiktok', 'instagram') else '30-60 sec'}",
        "media_ready": has_media_provider,
        "media_note": (
            "Video generation job queued." if has_media_provider
            else "Script-ready — no video provider configured. Use script with your editing tool."
        ),
    }


def build_youtube_kit_structure(
    *,
    business: dict[str, Any],
    offer: str = "",
    objective: str = "",
) -> dict[str, Any]:
    biz_name = business.get("name") or "your business"
    category = business.get("category") or "topic"
    return {
        "output_type": "youtube_kit",
        "title_options": [
            f"[Title Option 1 — How {biz_name} solves {category} challenges]",
            f"[Title Option 2 — {offer or 'Why this matters'} | {biz_name}]",
            f"[Title Option 3 — The complete guide to {category} with {biz_name}]",
        ],
        "description": f"[YouTube description for {biz_name} — include keywords, chapters, links]",
        "thumbnail_prompt": f"Bold text on vibrant background: '{offer or objective or biz_name}' with contrast face/product",
        "intro_hook": f"[0–30 sec hook: why watch this video about {category}]",
        "outline": [
            "Introduction (0:00)",
            f"Problem context (0:30)",
            f"Solution / {offer or 'offer'} walkthrough (2:00)",
            "Proof / results (4:00)",
            "How to get started (5:30)",
            "Call to action (7:00)",
        ],
        "chapters": "[Chapter timestamps — fill in after recording]",
        "tags_keywords": [category, biz_name, offer or objective, "how to", "guide"],
        "shorts_cutdown_idea": "[Cut scene 3–4 into a 60-sec YouTube Short]",
    }


def build_talking_avatar_structure(
    *,
    business: dict[str, Any],
    offer: str = "",
    audience: str = "",
    has_avatar_provider: bool = False,
) -> dict[str, Any]:
    biz_name = business.get("name") or "your business"
    return {
        "output_type": "talking_avatar",
        "avatar_persona": f"Professional spokesperson for {biz_name}",
        "script": (
            f"Hi, I'm representing {biz_name}. "
            f"If you're {audience or 'looking for a solution'}, "
            f"we have something for you: {offer or 'a great offer'}. "
            f"Here's why it matters and how to get started..."
        ),
        "delivery_notes": "Confident, friendly, clear pacing. Pause after key points.",
        "background_visual_brief": f"Clean branded background with {biz_name} colours or logo",
        "captions": "[Auto-generated from script — add SRT/VTT to video]",
        "media_job": "Avatar generation job queued." if has_avatar_provider else None,
        "avatar_ready": has_avatar_provider,
        "avatar_note": (
            "Avatar video will be generated by your configured provider."
            if has_avatar_provider
            else "No avatar provider configured — script is ready to record manually or use a third-party tool."
        ),
    }


def build_image_creative_structure(
    *,
    business: dict[str, Any],
    offer: str = "",
    platform: str = "",
    has_image_provider: bool = False,
) -> dict[str, Any]:
    biz_name = business.get("name") or "your business"
    category = business.get("category") or "business"
    return {
        "output_type": "image_creative_set",
        "creative_brief": (
            f"Brand: {biz_name}. Category: {category}. "
            f"Offer: {offer or 'key service/product'}. "
            f"Mood: professional, trustworthy, on-brand."
        ),
        "image_concepts": [
            {"concept": 1, "description": f"Hero shot — {offer or category} in action", "style": "Product/lifestyle photo"},
            {"concept": 2, "description": "Social proof — result or transformation visual", "style": "Before/after or testimonial card"},
            {"concept": 3, "description": f"Offer card — bold headline + CTA for {offer or 'the promotion'}", "style": "Graphic design with brand colours"},
        ],
        "pixabay_suggestions": [
            f"{category} professional",
            f"{offer or category} result",
            f"{biz_name.split()[0] if biz_name else category} team",
        ],
        "image_job": "Image generation job queued." if has_image_provider else None,
        "copy_overlay": f"[Headline] · {offer or 'Your offer'} · [CTA]",
        "cta_overlay": _cta_for_objective("sales"),
        "aspect_ratios": _aspect_ratios_for_platform(platform),
        "media_ready": has_image_provider,
        "image_note": (
            "Image generation available via your configured provider."
            if has_image_provider
            else "No image provider configured — use Pixabay suggestions or upload your own assets."
        ),
    }


def build_voiceover_structure(
    *,
    business: dict[str, Any],
    offer: str = "",
    has_tts_provider: bool = False,
) -> dict[str, Any]:
    biz_name = business.get("name") or "your business"
    return {
        "output_type": "voiceover",
        "script": (
            f"Welcome to {biz_name}. "
            f"We help you {offer or 'achieve your goals'} with proven results. "
            f"Ready to get started? Reach out today."
        ),
        "delivery_notes": "Warm, clear, professional. Moderate pace. Emphasis on key offer words.",
        "duration_estimate": "~20–30 seconds at natural speaking pace",
        "tts_job": "TTS generation job queued." if has_tts_provider else None,
        "voice_ready": has_tts_provider,
        "voice_note": (
            "Text-to-speech generation will be queued with your configured provider."
            if has_tts_provider
            else "No TTS provider configured — script is ready to record manually."
        ),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cta_for_objective(objective: str) -> str:
    mapping = {
        "awareness": "Learn More",
        "leads": "Get Free Consultation",
        "bookings": "Book Now",
        "sales": "Shop Now",
        "launch": "Join the Waitlist",
        "retargeting": "See What You Missed",
        "engagement": "Join the Conversation",
    }
    return mapping.get(objective.lower(), "Get Started")


def _placement_for_platform(platform: str) -> str:
    mapping = {
        "facebook": "Facebook Feed + Stories",
        "instagram": "Instagram Feed + Reels + Stories",
        "linkedin": "LinkedIn Feed",
        "tiktok": "TikTok For You Page",
        "youtube": "YouTube Pre-roll + In-feed",
        "twitter": "Twitter / X Timeline",
        "pinterest": "Pinterest Smart Feed",
    }
    return mapping.get((platform or "").lower(), "Primary feed placement")


def _aspect_ratios_for_platform(platform: str) -> dict[str, str]:
    base = {"square": "1:1 (1080×1080)", "portrait": "4:5 (1080×1350)", "landscape": "16:9 (1920×1080)"}
    extras: dict[str, dict[str, str]] = {
        "instagram": {"story": "9:16 (1080×1920)", "reel": "9:16 (1080×1920)"},
        "tiktok": {"tiktok": "9:16 (1080×1920)"},
        "linkedin": {"linkedin_banner": "4:1 (1584×396)"},
        "pinterest": {"pin": "2:3 (1000×1500)"},
        "youtube": {"thumbnail": "16:9 (1280×720)"},
    }
    result = {**base}
    result.update(extras.get((platform or "").lower(), {}))
    return result
