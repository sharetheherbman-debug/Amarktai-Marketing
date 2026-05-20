from __future__ import annotations

from typing import Any

from app.services.platform_catalog import normalize_platform
from app.services.qwen_router import route_qwen_model

_COST_HINTS: dict[str, dict[str, str]] = {
    "budget": {"image": "$0.001–0.005/img", "video": "$0.01–0.05/clip", "text": "$0.0001–0.001/1k tokens", "voice": "$0.001–0.005/min"},
    "balanced": {"image": "$0.005–0.02/img", "video": "$0.05–0.2/clip", "text": "$0.001–0.005/1k tokens", "voice": "$0.005–0.02/min"},
    "premium": {"image": "$0.02–0.10/img", "video": "$0.2–1.0/clip", "text": "$0.005–0.02/1k tokens", "voice": "$0.02–0.10/min"},
}

_MULTIMODAL_CAPABILITIES = {
    "image_generation", "video_generation", "talking_avatar_video",
    "text_to_speech", "voice_cloning", "image_editing", "video_editing",
}


def _output_type(capability: str, fmt: str) -> str:
    if "image" in capability or "image" in fmt:
        return "image"
    if "video" in capability or "video" in fmt or "avatar" in capability:
        return "video"
    if "speech" in capability or "voice" in capability or "tts" in capability:
        return "audio"
    return "text"


def _budget_tier(budget_mode: str, is_multimodal: bool) -> str:
    if budget_mode == "premium":
        return "premium"
    if budget_mode == "budget" and not is_multimodal:
        return "budget"
    return "balanced"


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
    out_type = _output_type(capability, fmt)
    is_multimodal = capability in _MULTIMODAL_CAPABILITIES or fmt in {"generated_image", "talking_avatar_video", "video_clip", "audio_clip"}
    budget_tier = _budget_tier(budget_mode, is_multimodal)
    can_generate_asset = is_multimodal
    risk_notes: list[str] = []

    if budget_mode not in {"auto", "budget", "balanced", "premium", "manual"}:
        risk_notes.append(f"Unknown budget_mode '{budget_mode}' — defaulting to auto.")
        budget_mode = "auto"

    # GenX preferred for premium/multimodal
    if is_multimodal and provider_keys.get("genx"):
        fallback_chain = ["genx", "qwen", "huggingface", "template"]
        preferred_model = (genx_catalog or {}).get("preferred_model") or "catalog_discovery_required"
        cost_hint = _COST_HINTS.get(budget_tier, {}).get(out_type, "unknown")
        return {
            "provider": "genx",
            "model": preferred_model,
            "selected_provider": "genx",
            "selected_model_or_task": preferred_model,
            "fallback_chain": fallback_chain,
            "reason": "Premium or multimodal task routed to GenX.",
            "budget_tier": budget_tier,
            "expected_output_type": out_type,
            "can_generate_asset": can_generate_asset,
            "estimated_cost_hint": cost_hint,
            "risk_notes": risk_notes,
        }

    # Qwen for text/budget/translation/learning
    if provider_keys.get("qwen"):
        qwen_cap = "image" if "image" in capability or "image" in fmt else (
            "video" if "video" in capability or "video" in fmt else (
                "voice" if "tts" in capability or "voice" in capability or "speech" in capability else "text"
            )
        )
        route = route_qwen_model(qwen_cap, budget_mode)
        fallback_chain = ["qwen", "huggingface", "template"]
        cost_hint = _COST_HINTS.get(budget_tier, {}).get(out_type, "unknown")
        reason = (
            "Budget-friendly translation/learning task routed to Qwen."
            if capability in {"translation", "learning", "hashtag"}
            else "Budget-friendly task routed to Qwen."
        )
        return {
            "provider": "qwen",
            "model": route.get("model"),
            "selected_provider": "qwen",
            "selected_model_or_task": route.get("model"),
            "fallback_chain": fallback_chain,
            "reason": reason,
            "budget_tier": budget_tier,
            "expected_output_type": out_type,
            "can_generate_asset": can_generate_asset,
            "estimated_cost_hint": cost_hint,
            "risk_notes": risk_notes,
        }

    # Hugging Face as fallback
    if provider_keys.get("huggingface"):
        fallback_chain = ["huggingface", "template"]
        hf_model = (hf_tasks or {}).get("preferred_model") or capability
        risk_notes.append("HuggingFace free tier may have rate limits or model unavailability.")
        return {
            "provider": "huggingface",
            "model": hf_model,
            "selected_provider": "huggingface",
            "selected_model_or_task": hf_model,
            "fallback_chain": fallback_chain,
            "reason": "Task fallback routed to Hugging Face.",
            "budget_tier": "budget",
            "expected_output_type": out_type,
            "can_generate_asset": False,
            "estimated_cost_hint": "Free (with token) or low cost",
            "risk_notes": risk_notes,
        }

    # Template fallback
    risk_notes.append("No external provider keys configured — using template fallback. Add GENX_API_KEY or QWEN_API_KEY for real AI generation.")
    return {
        "provider": "template",
        "model": "template_fallback",
        "selected_provider": "template",
        "selected_model_or_task": "template_fallback",
        "fallback_chain": ["template"],
        "reason": "No external provider keys configured.",
        "budget_tier": "budget",
        "expected_output_type": out_type,
        "can_generate_asset": False,
        "estimated_cost_hint": "Free (template only)",
        "risk_notes": risk_notes,
    }
