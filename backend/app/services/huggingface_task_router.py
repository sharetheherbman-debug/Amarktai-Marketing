from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class HFTaskSpec:
    task: str
    endpoint_method: str
    defaults: list[str]
    env_override: str | None = None


TASK_SPECS: dict[str, HFTaskSpec] = {
    "text-generation": HFTaskSpec("text-generation", "POST /models/{model}", ["Qwen/Qwen2.5-72B-Instruct", "mistralai/Mistral-7B-Instruct-v0.2"], "HF_MODEL_TEXT_GENERATION"),
    "summarization": HFTaskSpec("summarization", "POST /models/{model}", ["facebook/bart-large-cnn"], "HF_MODEL_SUMMARIZATION"),
    "zero-shot-classification": HFTaskSpec("zero-shot-classification", "POST /models/{model}", ["facebook/bart-large-mnli"], "HF_MODEL_ZERO_SHOT"),
    "sentiment-analysis": HFTaskSpec("sentiment-analysis", "POST /models/{model}", ["distilbert-base-uncased-finetuned-sst-2-english"], "HF_MODEL_SENTIMENT"),
    "token-classification": HFTaskSpec("token-classification", "POST /models/{model}", ["dslim/bert-base-NER"], "HF_MODEL_TOKEN_CLASSIFICATION"),
    "keyword-extraction": HFTaskSpec("keyword-extraction", "POST /models/{model}", ["dslim/bert-base-NER"], "HF_MODEL_KEYWORD_EXTRACTION"),
    "text-to-image": HFTaskSpec("text-to-image", "POST /models/{model}", ["black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-xl-base-1.0"], "HF_MODEL_TEXT_TO_IMAGE"),
    "image-to-text": HFTaskSpec("image-to-text", "POST /models/{model}", ["nlpconnect/vit-gpt2-image-captioning"], "HF_MODEL_IMAGE_TO_TEXT"),
    "text-to-speech": HFTaskSpec("text-to-speech", "POST /models/{model}", ["suno/bark-small"], "HF_MODEL_TEXT_TO_SPEECH"),
    "automatic-speech-recognition": HFTaskSpec("automatic-speech-recognition", "POST /models/{model}", ["openai/whisper-base"], "HF_MODEL_ASR"),
    "image-classification": HFTaskSpec("image-classification", "POST /models/{model}", ["google/vit-base-patch16-224"], "HF_MODEL_IMAGE_CLASSIFICATION"),
    "video-classification": HFTaskSpec("video-classification", "POST /models/{model}", ["MCG-NJU/videomae-base"], "HF_MODEL_VIDEO_CLASSIFICATION"),
    "image-to-video": HFTaskSpec("image-to-video", "POST /models/{model}", [], "HF_MODEL_IMAGE_TO_VIDEO"),
    "text-to-video": HFTaskSpec("text-to-video", "POST /models/{model}", ["damo-vilab/text-to-video-ms-1.7b"], "HF_MODEL_TEXT_TO_VIDEO"),
    "embeddings": HFTaskSpec("embeddings", "POST /models/{model}", ["sentence-transformers/all-MiniLM-L6-v2"], "HF_MODEL_EMBEDDINGS"),
    "sentence-similarity": HFTaskSpec("sentence-similarity", "POST /models/{model}", ["sentence-transformers/all-MiniLM-L6-v2"], "HF_MODEL_SENTENCE_SIMILARITY"),
}


class HuggingFaceTaskRouter:
    def __init__(self, token: str | None = None):
        self.token = token or settings.HUGGINGFACE_TOKEN

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def task_status(self, task: str, override_model: str | None = None) -> dict[str, Any]:
        spec = TASK_SPECS.get(task)
        if not spec:
            return {
                "task": task,
                "status": "not_implemented",
                "available": False,
                "model": "",
                "endpoint_method": "n/a",
                "debug": {"reason": "Task is not mapped."},
            }
        env_model = getattr(settings, spec.env_override or "", "") if spec.env_override else ""
        model = (override_model or env_model or (spec.defaults[0] if spec.defaults else "")).strip()
        if not self.configured:
            return {
                "task": task,
                "status": "missing_token",
                "available": False,
                "model": model,
                "defaults": spec.defaults,
                "endpoint_method": spec.endpoint_method,
                "debug": {"token_configured": False},
            }
        if not model:
            return {
                "task": task,
                "status": "not_implemented",
                "available": False,
                "model": "",
                "defaults": spec.defaults,
                "endpoint_method": spec.endpoint_method,
                "debug": {"reason": "No model configured for task."},
            }
        return {
            "task": task,
            "status": "available",
            "available": True,
            "model": model,
            "defaults": spec.defaults,
            "endpoint_method": spec.endpoint_method,
            "debug": {"token_configured": True, "override_applied": bool(override_model)},
        }

    def list_tasks(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "tasks": [self.task_status(task) for task in sorted(TASK_SPECS.keys())],
        }

    async def test_task(self, task: str, *, model_override: str | None = None) -> dict[str, Any]:
        status_payload = self.task_status(task, override_model=model_override)
        if status_payload["status"] != "available":
            return {
                **status_payload,
                "ok": False,
                "status": status_payload["status"],
            }
        model = status_payload["model"]
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"inputs": "Hello from AmarktAI Marketing."}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"https://api-inference.huggingface.co/models/{model}", headers=headers, json=payload)
            ok = response.status_code < 400
            return {
                **status_payload,
                "ok": ok,
                "status": "available" if ok else "provider_error",
                "http_status": response.status_code,
                "provider_error": None if ok else f"HF returned HTTP {response.status_code}",
            }
        except Exception as exc:
            return {
                **status_payload,
                "ok": False,
                "status": "provider_error",
                "provider_error": str(exc)[:300],
            }
