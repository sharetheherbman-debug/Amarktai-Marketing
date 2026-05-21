from __future__ import annotations

from typing import Any

from app.services.platform_catalog import normalize_platform
from app.services.qwen_router import route_qwen_model

_MEDIA_CAPABILITIES = {"image", "video", "voice", "avatar", "premium_creative"}


def _normalize_capability(capability: str, fmt: str, intent: str) -> str:
    lowered = (capability or "").lower()
    if lowered in {"image_generation", "image_editing", "image"} or "image" in fmt:
        return "image"
    if lowered in {"video_generation", "video", "talking_avatar_video"} or "video" in fmt or intent == "short_video":
        return "video"
    if lowered in {"text_to_speech", "voice", "audio", "text_to_audio"} or "voice" in fmt or "audio" in fmt:
        return "voice"
    if lowered in {"avatar", "talking_avatar", "avatar_video"} or "avatar" in fmt or intent == "talking_avatar":
        return "avatar"
    if intent in {"ad_campaign", "youtube_kit", "platform_pack"}:
        return "premium_creative"
    return "text"


def _mapping_for(capability: str, model_mappings: dict[str, str] | None) -> str:
    if not model_mappings:
        return ""
    return str(model_mappings.get(capability) or "").strip()


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
    intent: str | None = None,
    provider_mode: str = "auto",
    model_mappings: dict[str, str] | None = None,
    capability_availability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = intent or fmt or "quick_post"
    platform = normalize_platform(platform)
    resolved_capability = _normalize_capability(capability, fmt, intent)
    allow_fallback = provider_mode in {"auto", "fallback", "balanced"}
    genx_mapping = _mapping_for(resolved_capability, model_mappings)
    genx_available = bool(provider_keys.get("genx"))
    qwen_available = bool(provider_keys.get("qwen"))
    hf_available = bool(provider_keys.get("huggingface"))
    pixabay_available = bool(provider_keys.get("pixabay"))
    provider_attempt_order: list[str] = []

    def pack(
        *,
        selected_provider: str,
        selected_model_or_task: str,
        fallback_chain: list[str],
        media_state: str,
        can_generate_asset: bool,
        reason: str,
        user_message: str,
        status: str = "configured",
    ) -> dict[str, Any]:
        return {
            "provider": selected_provider,
            "model": selected_model_or_task,
            "selected_provider": selected_provider,
            "selected_model_or_task": selected_model_or_task,
            "capability": resolved_capability,
            "fallback_chain": fallback_chain,
            "media_state": media_state,
            "can_generate_asset": can_generate_asset,
            "reason": reason,
            "user_message": user_message,
            "status": status,
            "provider_attempt_order": provider_attempt_order or [selected_provider],
        }

    if resolved_capability in _MEDIA_CAPABILITIES:
        provider_attempt_order.extend(["genx", "qwen", "huggingface", "pixabay", "script_only"])
        if genx_available:
            capability_flag = bool((capability_availability or {}).get("genx", {}).get(resolved_capability, True))
            if not genx_mapping:
                return pack(
                    selected_provider="genx",
                    selected_model_or_task="",
                    fallback_chain=["qwen", "huggingface", "pixabay", "script_only"] if allow_fallback else ["script_only"],
                    media_state="not_rendered",
                    can_generate_asset=False,
                    reason="GenX is configured but the required model mapping is missing.",
                    user_message="GenX model mapping is required before premium media can render.",
                    status="model_mapping_required",
                )
            if not capability_flag:
                return pack(
                    selected_provider="genx",
                    selected_model_or_task=genx_mapping,
                    fallback_chain=["qwen", "huggingface", "pixabay", "script_only"] if allow_fallback else ["script_only"],
                    media_state="unavailable",
                    can_generate_asset=False,
                    reason="GenX key is present but the requested capability is unavailable.",
                    user_message="GenX is connected, but this media capability is unavailable for the mapped model.",
                    status="capability_unavailable",
                )
            return pack(
                selected_provider="genx",
                selected_model_or_task=genx_mapping,
                fallback_chain=["qwen", "huggingface", "pixabay", "script_only"],
                media_state="not_rendered",
                can_generate_asset=True,
                reason="GenX is the premium multimodal provider for this task.",
                user_message="GenX will be used as the premium multimodal engine.",
            )
        if resolved_capability in {"image", "video"} and pixabay_available:
            return pack(
                selected_provider="pixabay",
                selected_model_or_task="asset_search",
                fallback_chain=["script_only"],
                media_state="asset_search_result",
                can_generate_asset=False,
                reason="Using a real stock asset search provider instead of fake generated media.",
                user_message="Real stock assets will be suggested with source metadata.",
            )
        if resolved_capability in {"voice", "avatar", "video"}:
            script_message = "A truthful script-only result will be returned until premium media is configured."
            if qwen_available and allow_fallback:
                route = route_qwen_model("text", budget_mode)
                return pack(
                    selected_provider="qwen",
                    selected_model_or_task=str(route.get("model") or "qwen"),
                    fallback_chain=["huggingface", "script_only"],
                    media_state="script_only",
                    can_generate_asset=False,
                    reason="Falling back to Qwen for script generation while premium media stays unrendered.",
                    user_message=script_message,
                )
            if hf_available and allow_fallback:
                return pack(
                    selected_provider="huggingface",
                    selected_model_or_task=str((hf_tasks or {}).get("preferred_model") or resolved_capability),
                    fallback_chain=["script_only"],
                    media_state="script_only",
                    can_generate_asset=False,
                    reason="Hugging Face is being used only as a task fallback.",
                    user_message=script_message,
                )
            return pack(
                selected_provider="script_only",
                selected_model_or_task="script_only",
                fallback_chain=["script_only"],
                media_state="script_only",
                can_generate_asset=False,
                reason="No premium media provider is configured.",
                user_message=script_message,
            )

    provider_attempt_order.extend(["genx", "qwen", "huggingface", "script_only"])
    if genx_available and _mapping_for("text", model_mappings):
        return pack(
            selected_provider="genx",
            selected_model_or_task=_mapping_for("text", model_mappings),
            fallback_chain=["qwen", "huggingface", "script_only"],
            media_state="not_rendered",
            can_generate_asset=False,
            reason="GenX is used for premium text and creative generation.",
            user_message="GenX will be used for premium creative output.",
        )
    if qwen_available:
        route = route_qwen_model("text", budget_mode)
        return pack(
            selected_provider="qwen",
            selected_model_or_task=str(route.get("model") or "qwen"),
            fallback_chain=["huggingface", "script_only"],
            media_state="not_rendered",
            can_generate_asset=False,
            reason="Qwen is the budget and high-volume text router.",
            user_message="Qwen will generate the creative text for this request.",
        )
    if hf_available and allow_fallback:
        return pack(
            selected_provider="huggingface",
            selected_model_or_task=str((hf_tasks or {}).get("preferred_model") or resolved_capability),
            fallback_chain=["script_only"],
            media_state="not_rendered",
            can_generate_asset=False,
            reason="Hugging Face is only being used as a task fallback.",
            user_message="Hugging Face fallback is active for this task.",
        )
    return pack(
        selected_provider="script_only",
        selected_model_or_task="script_only",
        fallback_chain=["script_only"],
        media_state="unavailable",
        can_generate_asset=False,
        reason="No configured provider is available for this request.",
        user_message="No live provider is configured yet, so only a truthful script-only result is available.",
        status="not_configured",
    )
