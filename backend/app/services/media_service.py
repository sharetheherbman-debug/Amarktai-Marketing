"""Truthful media helpers for live and demo media generation."""

from __future__ import annotations

import base64
from typing import Any

import httpx

# HuggingFace models
_HF_FLUX_MODEL = "black-forest-labs/FLUX.1-schnell"
_HF_SDXL_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
_HF_VIDEO_MODEL = "damo-vilab/text-to-video-ms-1.7b"
_HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model}"

_PLATFORM_DIMENSIONS: dict[str, tuple[int, int]] = {
    "instagram": (1080, 1080),
    "facebook": (1200, 630),
    "twitter": (1600, 900),
    "linkedin": (1200, 627),
    "pinterest": (1000, 1500),
    "tiktok": (1080, 1920),
    "youtube": (1280, 720),
    "reddit": (1200, 628),
    "bluesky": (1200, 628),
    "threads": (1080, 1080),
    "telegram": (1280, 720),
    "snapchat": (1080, 1920),
}

VIDEO_PLATFORMS = {"youtube", "tiktok", "snapchat"}

# HuggingFace inference steps — low value = fast generation, suitable for Pro tier
# FLUX.1-schnell is designed for 4-step inference; SDXL works well at 20-25 steps
_FLUX_INFERENCE_STEPS = 4
_SDXL_INFERENCE_STEPS = 20
_VIDEO_INFERENCE_STEPS = 25


async def get_media_url(
    platform: str,
    webapp_data: dict[str, Any],
    hf_token: str | None = None,
    image_prompt: str | None = None,
) -> list[str]:
    """Return real generated media only; demo placeholders stay opt-in."""
    if platform in VIDEO_PLATFORMS:
        if hf_token:
            url = await _generate_hf_video(hf_token, webapp_data, platform)
            if url:
                return [url]
        return [_get_demo_video()] if settings.ENABLE_DEMO_MEDIA else []

    if hf_token:
        prompt = image_prompt or _build_image_prompt(webapp_data, platform)
        url = await _generate_hf_image(hf_token, prompt, platform)
        if url:
            return [url]

    return [_get_demo_image(platform)] if settings.ENABLE_DEMO_MEDIA else []


async def _generate_hf_image(hf_token: str, prompt: str, platform: str) -> str | None:
    """Generate image via HF FLUX.1-schnell (then SDXL fallback). Returns None on failure."""
    w, h = _PLATFORM_DIMENSIONS.get(platform, (1080, 1080))
    for model in [_HF_FLUX_MODEL, _HF_SDXL_MODEL]:
        url = _HF_INFERENCE_URL.format(model=model)
        try:
            headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            payload = {"inputs": prompt, "parameters": {"width": min(w, 1024), "height": min(h, 1024), "num_inference_steps": _FLUX_INFERENCE_STEPS}}
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    if content_type.startswith("image/"):
                        # Return as data URI (works without external storage)
                        b64 = base64.b64encode(resp.content).decode()
                        ext = "jpeg" if "jpeg" in content_type else "png"
                        return f"data:image/{ext};base64,{b64}"
                elif resp.status_code == 503:
                    continue  # model loading
        except Exception:
            continue
    return None


async def _generate_hf_video(hf_token: str, webapp_data: dict[str, Any], platform: str) -> str | None:
    """
    Generate a short video clip via HuggingFace text-to-video.
    """
    name = webapp_data.get("name", "product")
    description = webapp_data.get("description", "")[:100]
    prompt = f"Professional marketing video for {name}: {description}. Modern, clean, corporate style."

    url = _HF_INFERENCE_URL.format(model=_HF_VIDEO_MODEL)
    try:
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {"inputs": prompt, "parameters": {"num_frames": 16, "num_inference_steps": _VIDEO_INFERENCE_STEPS}}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                if "video" in content_type or "gif" in content_type or resp.headers.get("content-length", "0") != "0":
                    b64 = base64.b64encode(resp.content).decode()
                    return f"data:video/mp4;base64,{b64}"
    except Exception:
        pass
    return None

def _get_demo_image(platform: str) -> str:
    w, h = _PLATFORM_DIMENSIONS.get(platform, (1080, 1080))
    return f"https://picsum.photos/seed/demo/{w}/{h}"


def _get_demo_video() -> str:
    return "https://assets.mixkit.co/videos/preview/mixkit-typing-on-a-laptop-in-a-coffee-shop-484-large.mp4"


# Public aliases — use these outside this module instead of the private variants
def placeholder_image(webapp_data: dict[str, Any], platform: str) -> str:
    """Demo-only placeholder image."""
    return _get_demo_image(platform)


def placeholder_video(webapp_data: dict[str, Any]) -> str:
    """Demo-only placeholder video."""
    return _get_demo_video()


def _build_image_prompt(webapp_data: dict[str, Any], platform: str) -> str:
    name = webapp_data.get("name", "product")
    category = webapp_data.get("category", "SaaS")
    audience = webapp_data.get("target_audience", "professionals")
    return (
        f"Professional {platform} marketing image for {name}, a {category} tool for {audience}. "
        "Sleek modern UI mockup, clean minimalist design, purple-blue gradient background, "
        "high quality, photorealistic, no text, no watermarks, 4K render."
    )
