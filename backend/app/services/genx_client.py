from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GenXClient:
    """GenX client with task-aware model routing and in-provider fallbacks."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        default_model: str = "",
        timeout: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.GENX_API_KEY
        self.base_url = (base_url or settings.GENX_BASE_URL or "").rstrip("/")
        self.default_model = default_model or settings.GENX_DEFAULT_MODEL
        self.timeout = timeout or settings.GENX_TIMEOUT or 60
        self.allowlist = {
            m.strip()
            for m in (settings.GENX_MODEL_ALLOWLIST or "").split(",")
            if m.strip()
        }
        self.fallback_models = [
            m.strip()
            for m in (settings.GENX_MODEL_FALLBACKS or "").split(",")
            if m.strip()
        ]
        self.task_models = {
            "copy": settings.GENX_MODEL_COPY or "",
            "strategy": settings.GENX_MODEL_STRATEGY or "",
            "analysis": settings.GENX_MODEL_ANALYSIS or "",
            "long_form": settings.GENX_MODEL_LONG_FORM or "",
            "moderation": settings.GENX_MODEL_MODERATION or "",
        }

    @property
    def ready(self) -> bool:
        return bool(self.api_key and self.base_url and self.default_model)

    async def health_check(self) -> dict[str, Any]:
        """
        Probe GenX connectivity.

        Returns a dict with keys:
          - ``ok`` (bool): True when a test request succeeds.
          - ``latency_ms`` (int): Round-trip time in milliseconds (0 when not ok).
          - ``model`` (str): Model used for the probe.
          - ``error`` (str | None): Error description when not ok.
        """
        if not self.ready:
            return {
                "ok": False,
                "latency_ms": 0,
                "model": self.default_model,
                "error": "GenX client is not configured (missing api_key, base_url, or default_model).",
            }
        started = time.perf_counter()
        try:
            result = await self.generate_text(
                "Reply with one word: ok",
                system="You are a health-check assistant.",
                task="copy",
                max_tokens=5,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if result:
                return {"ok": True, "latency_ms": latency_ms, "model": result.get("model", ""), "error": None}
            return {
                "ok": False,
                "latency_ms": latency_ms,
                "model": self.default_model,
                "error": "GenX returned an empty response during health check.",
            }
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": False,
                "latency_ms": latency_ms,
                "model": self.default_model,
                "error": str(exc),
            }

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _model_for_task(self, task: str, requested_model: str | None = None) -> list[str]:
        primary = requested_model or self.task_models.get(task) or self.default_model
        candidates = [primary, *self.fallback_models]
        seen: set[str] = set()
        ordered: list[str] = []
        for model in candidates:
            if not model or model in seen:
                continue
            seen.add(model)
            if self.allowlist and model not in self.allowlist:
                continue
            ordered.append(model)
        if not ordered and primary:
            ordered.append(primary)
        return ordered

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {})
            if isinstance(msg, dict) and msg.get("content"):
                return str(msg.get("content"))
            text = choices[0].get("text")
            if text:
                return str(text)
        if data.get("output_text"):
            return str(data.get("output_text"))
        if data.get("text"):
            return str(data.get("text"))
        return ""

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str = "",
        task: str = "copy",
        max_tokens: int = 512,
        temperature: float = 0.8,
        model: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.ready:
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        endpoint = self._endpoint()
        model_candidates = self._model_for_task(task, model)
        for candidate in model_candidates:
            payload = {
                "model": candidate,
                "messages": [
                    {"role": "system", "content": system or "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(endpoint, headers=headers, json=payload)
                latency_ms = int((time.perf_counter() - started) * 1000)
                if resp.status_code >= 400:
                    logger.warning(
                        "GenX model '%s' returned HTTP %s (latency=%dms). Trying next candidate.",
                        candidate,
                        resp.status_code,
                        latency_ms,
                    )
                    continue
                data = resp.json()
                text = self._extract_text(data)
                if not text:
                    logger.debug("GenX model '%s' returned empty text. Trying next candidate.", candidate)
                    continue
                usage = data.get("usage", {}) if isinstance(data, dict) else {}
                logger.debug(
                    "GenX model '%s' succeeded (latency=%dms, tokens=%s).",
                    candidate,
                    latency_ms,
                    usage.get("total_tokens", "?"),
                )
                return {
                    "text": text,
                    "provider": "genx",
                    "model": candidate,
                    "tokens": usage.get("total_tokens", 0),
                    "cost_usd": usage.get("cost_usd", 0.0),
                    "latency_ms": latency_ms,
                }
            except Exception as exc:
                latency_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "GenX model '%s' raised an exception after %dms: %s",
                    candidate,
                    latency_ms,
                    exc,
                )
                continue
        logger.error(
            "All GenX model candidates exhausted without a successful response. "
            "Candidates tried: %s. Check GENX_API_KEY, GENX_BASE_URL, and model configuration.",
            model_candidates,
        )
        return None
