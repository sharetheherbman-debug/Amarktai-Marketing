from __future__ import annotations

from typing import Any

from app.services.platform_catalog import normalize_platform


PLATFORM_FORMATS: dict[str, list[str]] = {
    "tiktok": ["short_video_brief", "hook", "shot_list", "voiceover_script", "caption", "hashtags"],
    "youtube": ["title", "description", "video_script", "thumbnail_prompt", "chapters", "shorts_cutdown"],
    "instagram": ["caption", "image_prompt", "carousel_outline", "reels_script"],
    "facebook": ["caption", "image_prompt", "cta", "community_question"],
    "linkedin": ["professional_post", "image_prompt", "article_angle", "authority_hook"],
    "twitter": ["short_post", "thread", "engagement_question"],
    "reddit": ["discussion_post", "human_review_warning"],
    "pinterest": ["pin_title", "description", "image_prompt", "keyword_copy"],
}


def select_formats(platform: str, requested_format: str | None = None, auto_select: bool = True) -> dict[str, Any]:
    key = normalize_platform(platform)
    defaults = PLATFORM_FORMATS.get(key, ["caption"])
    if auto_select or not requested_format:
        return {"platform": key, "formats": defaults, "auto_selected": True}
    if requested_format not in defaults:
        return {"platform": key, "formats": [requested_format, *defaults[:2]], "auto_selected": False}
    return {"platform": key, "formats": [requested_format], "auto_selected": False}
