from __future__ import annotations

from typing import Any

from app.services.platform_catalog import normalize_platform
from app.services.qwen_router import route_qwen_model


def decide_provider(
    *,
    capability: str,
    platform: str,
    fmt: str,
    business: dict[str, Any] | None,
    budget_mode: str,
    provider_keys: dict[str, bool],
    genx_catalog: dict[str, Any] | None = None,
    qwen_catalog: dict[str, Any] | None = None,
    hf_tasks: dict[str, Any] | None = None,
    platform_intelligence: dict[str, Any] | None = None,
    learning_insights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    platform = normalize_platform(platform)
    fallback_chain: list[str] = []
    wants_multimodal = capability in {"image_generation", "video_generation", "talking_avatar_video", "text_to_speech"} or fmt in {"generated_image", "talking_avatar_video"}
    if wants_multimodal and provider_keys.get("genx"):
        fallback_chain = ["genx", "qwen", "huggingface", "template"]
        return {
            "provider": "genx",
            "model": ((genx_catalog or {}).get("preferred_model") or "catalog_discovery_required"),
            "fallback_chain": fallback_chain,
            "reason": "Premium or multimodal task routed to GenX first.",
        }
    if provider_keys.get("qwen"):
        route = route_qwen_model("image" if "image" in capability or "image" in fmt else ("video" if "video" in capability or "video" in fmt else "text"), budget_mode)
        fallback_chain = ["qwen", "huggingface", "template"]
        return {
            "provider": "qwen",
            "model": route.get("model"),
            "fallback_chain": fallback_chain,
            "reason": "Budget-friendly task routed to Qwen.",
        }
    if provider_keys.get("huggingface"):
        fallback_chain = ["huggingface", "template"]
        return {
            "provider": "huggingface",
            "model": ((hf_tasks or {}).get("preferred_model") or capability),
            "fallback_chain": fallback_chain,
            "reason": "Task fallback routed to Hugging Face.",
        }
    return {
        "provider": "template",
        "model": "template_fallback",
        "fallback_chain": ["template"],
        "reason": "No external provider keys configured.",
    }
