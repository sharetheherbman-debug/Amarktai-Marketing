from __future__ import annotations

from typing import Any


CAPABILITIES: list[dict[str, Any]] = [
    {"id": "website_scrape", "label": "Website scrape", "description": "Scrape website content for business context.", "providers": ["firecrawl"], "output_type": "json", "dashboard_action": "Analyze Website", "requirements": ["FIRECRAWL_API_KEY"]},
    {"id": "business_intelligence", "label": "Business intelligence", "description": "Extract audience, keywords, and offers.", "providers": ["firecrawl", "qwen"], "output_type": "json", "dashboard_action": "Refresh Intelligence", "requirements": ["FIRECRAWL_API_KEY"]},
    {"id": "campaign_strategy", "label": "Campaign strategy", "description": "Build campaign strategy and messaging pillars.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Campaign Plan", "requirements": ["GENX_API_KEY", "QWEN_API_KEY"]},
    {"id": "platform_copy", "label": "Platform copy", "description": "Generate platform-ready post copy.", "providers": ["genx", "qwen", "huggingface"], "output_type": "text", "dashboard_action": "Generate Content", "requirements": ["GENX_API_KEY", "QWEN_API_KEY"]},
    {"id": "long_form_copy", "label": "Long-form copy", "description": "Generate long-form drafts.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Long Form", "requirements": ["GENX_API_KEY", "QWEN_API_KEY"]},
    {"id": "hashtags", "label": "Hashtags", "description": "Generate hashtag sets by platform.", "providers": ["genx", "qwen"], "output_type": "list", "dashboard_action": "Generate Content", "requirements": ["GENX_API_KEY", "QWEN_API_KEY"]},
    {"id": "compliance_review", "label": "Compliance review", "description": "Flag risky claims and compliance issues.", "providers": ["template", "genx"], "output_type": "json", "dashboard_action": "Review Content", "requirements": []},
    {"id": "algorithm_fit_review", "label": "Algorithm fit review", "description": "Evaluate fit for platform ranking patterns.", "providers": ["template", "genx"], "output_type": "json", "dashboard_action": "Review Content", "requirements": []},
    {"id": "terms_policy_review", "label": "Terms policy review", "description": "Check terms and policy risk indicators.", "providers": ["template", "genx"], "output_type": "json", "dashboard_action": "Review Content", "requirements": []},
    {"id": "image_prompt", "label": "Image prompt", "description": "Create image prompts for creatives.", "providers": ["genx", "qwen", "huggingface"], "output_type": "text", "dashboard_action": "Generate Creative", "requirements": ["QWEN_API_KEY"]},
    {"id": "image_generation", "label": "Image generation", "description": "Generate image assets when available.", "providers": ["genx", "huggingface"], "output_type": "image", "dashboard_action": "Generate Creative", "requirements": ["HUGGINGFACE_TOKEN"]},
    {"id": "carousel_outline", "label": "Carousel outline", "description": "Build carousel slide outlines.", "providers": ["genx", "qwen"], "output_type": "json", "dashboard_action": "Generate Creative", "requirements": ["QWEN_API_KEY"]},
    {"id": "thumbnail_prompt", "label": "Thumbnail prompt", "description": "Create thumbnail prompts.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Creative", "requirements": ["QWEN_API_KEY"]},
    {"id": "video_script", "label": "Video script", "description": "Generate video scripts and hooks.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Creative", "requirements": ["QWEN_API_KEY"]},
    {"id": "short_video_brief", "label": "Short video brief", "description": "Generate short-form video brief and shot list.", "providers": ["genx", "qwen"], "output_type": "json", "dashboard_action": "Generate Creative", "requirements": ["QWEN_API_KEY"]},
    {"id": "youtube_video_kit", "label": "YouTube kit", "description": "Generate full YouTube video kit.", "providers": ["genx", "qwen"], "output_type": "json", "dashboard_action": "Generate YouTube Kit", "requirements": ["QWEN_API_KEY"]},
    {"id": "tiktok_reels_kit", "label": "TikTok/Reels kit", "description": "Generate TikTok/Reels scripts and assets.", "providers": ["genx", "qwen"], "output_type": "json", "dashboard_action": "Generate TikTok/Reels Kit", "requirements": ["QWEN_API_KEY"]},
    {"id": "voiceover_script", "label": "Voiceover script", "description": "Generate voiceover script.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Creative", "requirements": ["QWEN_API_KEY"]},
    {"id": "text_to_speech", "label": "Text to speech", "description": "Generate speech from text where supported.", "providers": ["huggingface"], "output_type": "audio", "dashboard_action": "Generate Voiceover", "requirements": ["HUGGINGFACE_TOKEN"]},
    {"id": "talking_avatar_script", "label": "Talking avatar script", "description": "Generate avatar-ready scripts.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Talking Avatar", "requirements": ["QWEN_API_KEY"]},
    {"id": "talking_avatar_video", "label": "Talking avatar video", "description": "Generate avatar videos where supported.", "providers": ["genx", "huggingface"], "output_type": "video", "dashboard_action": "Generate Talking Avatar", "requirements": ["HUGGINGFACE_TOKEN"]},
    {"id": "video_generation", "label": "Video generation", "description": "Generate video assets where supported.", "providers": ["genx", "huggingface"], "output_type": "video", "dashboard_action": "Generate Creative", "requirements": ["HUGGINGFACE_TOKEN"]},
    {"id": "kling_video_generation", "label": "Kling video generation", "description": "Generate Kling videos when model exists.", "providers": ["genx"], "output_type": "video", "dashboard_action": "Generate Creative", "requirements": ["GENX_API_KEY"]},
    {"id": "content_calendar", "label": "Content calendar", "description": "Build calendar-ready schedule drafts.", "providers": ["template", "genx"], "output_type": "json", "dashboard_action": "Generate Calendar", "requirements": []},
    {"id": "schedule_planning", "label": "Schedule planning", "description": "Draft posting schedule plan.", "providers": ["template", "genx"], "output_type": "json", "dashboard_action": "Schedule Draft", "requirements": []},
    {"id": "performance_learning", "label": "Performance learning", "description": "Generate learning recommendations from metrics.", "providers": ["template", "genx"], "output_type": "json", "dashboard_action": "Run Learning", "requirements": []},
    {"id": "competitor_angle", "label": "Competitor angle", "description": "Generate competitor-aware angles.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Campaign Plan", "requirements": ["QWEN_API_KEY"]},
    {"id": "customer_acquisition_angle", "label": "Customer acquisition angle", "description": "Generate acquisition-focused messaging angles.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Campaign Plan", "requirements": ["QWEN_API_KEY"]},
    {"id": "follower_growth_angle", "label": "Follower growth angle", "description": "Generate growth-oriented messaging angles.", "providers": ["genx", "qwen"], "output_type": "text", "dashboard_action": "Generate Campaign Plan", "requirements": ["QWEN_API_KEY"]},
]


def build_capability_catalog(
    *,
    provider_resolution: dict[str, Any],
    readiness: dict[str, Any],
    implemented_services: set[str] | None = None,
) -> list[dict[str, Any]]:
    implemented_services = implemented_services or set()
    providers = provider_resolution.get("providers", {})
    details = readiness.get("provider_details", {})
    genx_status = (details.get("genx", {}) or {}).get("status")

    output: list[dict[str, Any]] = []
    for item in CAPABILITIES:
        required = item.get("requirements", [])
        missing = [key for key in required if (providers.get(key, {}) or {}).get("effective_source") == "missing"]
        service_name = item["id"]
        implemented = (not implemented_services) or (service_name in implemented_services)
        status = "available"
        degraded = False
        reason = ""
        if missing:
            status = "missing_provider"
            reason = f"Missing required keys: {', '.join(missing)}"
        elif genx_status == "model_invalid" and "genx" in item.get("providers", []):
            status = "model_invalid"
            degraded = True
            reason = "GenX model invalid; fallback provider should be used."
        elif not implemented:
            status = "not_implemented"
            reason = "Capability endpoint not implemented yet."
        elif (details.get("qwen", {}) or {}).get("status") == "fallback_available" and "genx" in item.get("providers", []):
            status = "degraded" if genx_status == "test_failed" else "available"
            degraded = status == "degraded"

        preferred_provider = item["providers"][0] if item["providers"] else "template"
        fallback_provider = next((provider for provider in item.get("providers", [])[1:] if provider != preferred_provider), None)
        output.append(
            {
                "id": item["id"],
                "label": item["label"],
                "description": item["description"],
                "status": status,
                "degraded": degraded,
                "reason": reason,
                "providers_available": item.get("providers", []),
                "preferred_provider": preferred_provider,
                "fallback_provider": fallback_provider,
                "required_key_names": required,
                "required_models_or_tasks": [],
                "output_type": item["output_type"],
                "dashboard_action": item["dashboard_action"],
            }
        )
    return output
