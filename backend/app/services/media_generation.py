from __future__ import annotations

from typing import Any

import httpx
import base64

from app.services.ai_provider import AIProvider
from app.services.huggingface_task_router import HuggingFaceTaskRouter

_HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model}"


async def _generate_text(webapp_data: dict[str, Any], prompt: str, *, qwen_key: str | None = None, hf_token: str | None = None, openai_key: str | None = None, genx_key: str | None = None) -> dict[str, Any]:
    provider = AIProvider.from_keys(
        qwen_key=qwen_key or "",
        hf_token=hf_token or "",
        openai_key=openai_key or "",
        genx_key=genx_key or "",
    )
    result_text = await provider.generate_text(prompt, max_tokens=700)
    if result_text:
        return {"text": result_text, "provider": "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template"))}
    return {"text": prompt[:500], "provider": "template"}


async def generate_image_prompt(webapp_data: dict[str, Any], platform: str, **kwargs: Any) -> dict[str, Any]:
    name = webapp_data.get("name", "the business")
    category = webapp_data.get("category", "")
    description = webapp_data.get("description", "")
    audience = webapp_data.get("target_audience", "")
    products = webapp_data.get("products_services") or webapp_data.get("key_features") or []
    products_str = ", ".join(str(p) for p in products[:3]) if isinstance(products, list) and products else str(products or "")
    category_line = f"Industry/category: {category}." if category else ""
    products_line = f"Products/services: {products_str}." if products_str else ""
    audience_line = f"Target audience: {audience}." if audience else ""
    prompt = (
        f"Create a high-quality {platform} image prompt for {name}. "
        f"{category_line} {products_line} {audience_line} "
        f"Description: {description}. "
        f"The image must be directly relevant to {name} and its industry ({category or 'business'}). "
        f"IMPORTANT: Do NOT use generic or unrelated imagery. "
        f"Do NOT show Amarktai branding unless {name} is Amarktai. "
        f"Show imagery that immediately communicates what {name} does."
    )
    generated = await _generate_text(webapp_data, prompt, **kwargs)
    return {"image_prompt": generated["text"], "provider": generated["provider"]}


async def generate_image_asset(*, image_prompt: str, hf_token: str | None = None) -> dict[str, Any]:
    router = HuggingFaceTaskRouter(token=hf_token)
    status = router.task_status("text-to-image")
    if status["status"] != "available":
        return {"image_url": None, "asset_generation_status": "prompt_or_script_only", "provider": "none"}
    model = status["model"]
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                _HF_INFERENCE_URL.format(model=model),
                headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                json={"inputs": image_prompt},
            )
        if response.status_code == 200 and response.headers.get("content-type", "").startswith("image/"):
            return {
                "image_url": f"data:{response.headers.get('content-type')};base64,{base64.b64encode(response.content).decode()}",
                "asset_generation_status": "generated",
                "provider": "huggingface",
            }
    except Exception:
        pass
    return {"image_url": None, "asset_generation_status": "prompt_or_script_only", "provider": "none"}


async def generate_video_script(webapp_data: dict[str, Any], platform: str, **kwargs: Any) -> dict[str, Any]:
    name = webapp_data.get("name", "the business")
    category = webapp_data.get("category", "")
    description = webapp_data.get("description", "")
    products = webapp_data.get("products_services") or webapp_data.get("key_features") or []
    products_str = ", ".join(str(p) for p in products[:3]) if isinstance(products, list) and products else str(products or "")
    prompt = (
        f"Write a concise {platform} video script for {name}. "
        f"Industry: {category}. Products/services: {products_str}. Description: {description}. "
        f"Structure: hook, 3 content beats specific to {name}, and CTA. "
        f"Keep the script grounded to what {name} actually does."
    )
    generated = await _generate_text(webapp_data, prompt, **kwargs)
    return {"video_script": generated["text"], "provider": generated["provider"]}


async def generate_short_video_brief(webapp_data: dict[str, Any], platform: str, **kwargs: Any) -> dict[str, Any]:
    script = await generate_video_script(webapp_data, platform, **kwargs)
    return {
        "video_script": script["video_script"],
        "shot_list": ["Hook shot", "Problem shot", "Solution shot", "CTA shot"],
        "provider": script["provider"],
    }


async def generate_youtube_kit(webapp_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    base = await generate_video_script(webapp_data, "youtube", **kwargs)
    return {
        "title": f"{webapp_data.get('name', 'Business')} — YouTube growth guide",
        "description": base["video_script"][:400],
        "video_script": base["video_script"],
        "thumbnail_prompt": "High-contrast thumbnail, clear subject, bold emotion, no guaranteed claims.",
        "chapters": ["Hook", "Core value", "Examples", "CTA"],
        "provider": base["provider"],
    }


async def generate_tiktok_reels_kit(webapp_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    base = await generate_short_video_brief(webapp_data, "tiktok", **kwargs)
    return {
        "hook": base["video_script"].split("\n")[0][:120],
        "video_script": base["video_script"],
        "shot_list": base["shot_list"],
        "caption": "Video-first short format with concise CTA.",
        "hashtags": ["#tiktoktips", "#reels", "#growth"],
        "provider": base["provider"],
    }


async def generate_voiceover_script(webapp_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    generated = await _generate_text(webapp_data, f"Write a 30-second voiceover script for {webapp_data.get('name', 'the business')}.", **kwargs)
    return {"voiceover_script": generated["text"], "provider": generated["provider"]}


async def generate_talking_avatar_script(webapp_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    generated = await _generate_text(webapp_data, f"Write a talking avatar script for {webapp_data.get('name', 'the business')} with realistic growth claims.", **kwargs)
    return {"avatar_script": generated["text"], "provider": generated["provider"]}


async def generate_talking_avatar_video(*, avatar_script: str, hf_token: str | None = None) -> dict[str, Any]:
    status = HuggingFaceTaskRouter(token=hf_token).task_status("text-to-video")
    if status["status"] != "available":
        return {"avatar_url": None, "asset_generation_status": "prompt_or_script_only", "provider": "none"}
    return {"avatar_url": None, "asset_generation_status": "prompt_or_script_only", "provider": "huggingface"}


async def generate_thumbnail_prompt(webapp_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    generated = await _generate_text(webapp_data, f"Write a thumbnail prompt for {webapp_data.get('name', 'the business')} YouTube video.", **kwargs)
    return {"thumbnail_prompt": generated["text"], "provider": generated["provider"]}


async def generate_carousel_outline(webapp_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    generated = await _generate_text(webapp_data, f"Create a 7-slide carousel outline for {webapp_data.get('name', 'the business')}.", **kwargs)
    slides = [line.strip("- ").strip() for line in generated["text"].split("\n") if line.strip()][:7]
    return {"carousel_slides": slides or ["Hook", "Problem", "Solution", "Proof", "CTA"], "provider": generated["provider"]}
