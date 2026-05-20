from __future__ import annotations

from typing import Any

QWEN_MODELS = [
    "qwen-flash",
    "qwen-plus",
    "qwen3.5-flash",
    "qwen3.6-flash",
    "qwen3.6-plus",
    "qwen3-max",
    "qwen3.6-max-preview",
    "qwen3-vl-flash",
    "qwen3-vl-plus",
    "qwen3.5-omni-flash",
    "qwen3.5-omni-plus",
    "qwen3-omni-flash",
    "qwen-omni-turbo",
    "qwen-image-2.0",
    "qwen-image-2.0-pro",
    "qwen-image-plus",
    "qwen-image-max",
    "qwen-image-edit-plus-2025-12-15",
    "qwen-image-edit-max",
    "wan2.6-t2i",
    "wan2.7-image-pro",
    "wan2.7-t2v",
    "wan2.7-i2v",
    "wan2.7-r2v",
    "wan2.7-videoedit",
    "wan2.1-vace-plus",
    "happyhorse-1.0-t2v",
    "happyhorse-1.0-i2v",
    "happyhorse-1.0-r2v",
    "happyhorse-1.0-video-edit",
    "qwen3-tts-flash",
    "qwen3-tts-flash-realtime",
    "qwen3-tts-instruct-flash",
    "qwen3-asr-flash",
    "qwen3-asr-flash-realtime",
    "qwen-voice-enrollment",
    "qwen3-tts-vc-realtime-2026-01-15",
    "qwen3-tts-vd-realtime-2026-01-15",
    "qwen-vl-ocr",
    "qwen-mt-flash",
    "qwen3-rerank",
    "text-embedding-v4",
]


def qwen_model_catalog() -> dict[str, Any]:
    return {
        "models": QWEN_MODELS,
        "by_capability": {
            "text": [model for model in QWEN_MODELS if "image" not in model and "wan" not in model and "tts" not in model and "asr" not in model and "embedding" not in model],
            "image": [model for model in QWEN_MODELS if "image" in model or "t2i" in model],
            "video": [model for model in QWEN_MODELS if "t2v" in model or "i2v" in model or "video" in model or "r2v" in model],
            "voice": [model for model in QWEN_MODELS if "tts" in model or "voice" in model or "asr" in model],
            "embedding": [model for model in QWEN_MODELS if "embedding" in model or "rerank" in model],
        },
    }
