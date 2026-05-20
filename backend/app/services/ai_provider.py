"""
AmarktAI Marketing — Unified AI Provider Abstraction
=====================================================

Priority order for text generation (lowest cost first):
  1. GenX — primary unified router (GENX_API_KEY)
  2. Qwen (Alibaba Cloud DashScope) — fallback (QWEN_API_KEY)
  3. HuggingFace Inference API — fallback (HUGGINGFACE_TOKEN)
  4. OpenAI — optional (OPENAI_API_KEY)
  5. Gemini — optional (GEMINI_API_KEY)
  6. Template fallback — always available

All external provider names are intentionally abstracted here.
Callers receive metadata indicating which provider was used.

Usage
-----
    from app.services.ai_provider import AIProvider

    provider = AIProvider.from_settings()
    result = await provider.generate_content(webapp_data, platform)
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.services.genx_client import GenXClient

logger = logging.getLogger(__name__)

_DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
_HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model}"
_HF_DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
_HF_FALLBACK_MODEL = "distilgpt2"
_OPENAI_MODEL = "gpt-3.5-turbo"
_GEMINI_MODEL = "gemini-pro"


class AIProvider:
    """
    Unified AI provider that walks down a priority chain:
    AmarktAI Network → GenX → Qwen → HuggingFace → OpenAI → Gemini → Template.

    When AMARKTAI_INTEGRATION_ENABLED=true and a valid integration token is
    configured, the AmarktAI Network super brain is used as the top-priority
    provider.  If it is unavailable or not configured, the chain falls through
    to local providers transparently.
    """

    def __init__(
        self,
        qwen_key: str = "",
        hf_token: str = "",
        openai_key: str = "",
        gemini_key: str = "",
        genx_key: str = "",
    ) -> None:
        self._qwen_key = qwen_key or ""
        self._hf_token = hf_token or ""
        self._openai_key = openai_key or ""
        self._gemini_key = gemini_key or ""
        self._genx_key = genx_key or ""
        self._genx = GenXClient(api_key=self._genx_key)

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_settings(cls) -> "AIProvider":
        """Build from global settings (system-level keys only)."""
        gemini_key = settings.GEMINI_API_KEY or settings.GOOGLE_GEMINI_API_KEY or ""
        return cls(
            genx_key=settings.GENX_API_KEY,
            qwen_key=settings.QWEN_API_KEY,
            hf_token=settings.HUGGINGFACE_TOKEN,
            openai_key=settings.OPENAI_API_KEY,
            gemini_key=gemini_key,
        )

    @classmethod
    def from_keys(
        cls,
        qwen_key: str = "",
        hf_token: str = "",
        openai_key: str = "",
        gemini_key: str = "",
        genx_key: str = "",
    ) -> "AIProvider":
        """Build with explicit key overrides (e.g. from per-user DB keys)."""
        gemini_fallback = settings.GEMINI_API_KEY or settings.GOOGLE_GEMINI_API_KEY or ""
        return cls(
            genx_key=genx_key or settings.GENX_API_KEY,
            qwen_key=qwen_key or settings.QWEN_API_KEY,
            hf_token=hf_token or settings.HUGGINGFACE_TOKEN,
            openai_key=openai_key or settings.OPENAI_API_KEY,
            gemini_key=gemini_key or gemini_fallback,
        )

    # Backwards-compatible factory used by existing callers
    @classmethod
    def from_env_or_db(
        cls,
        hf_token: str = "",
        qwen_key: str = "",
        openai_key: str = "",
        genx_key: str = "",
    ) -> "AIProvider":
        return cls.from_keys(
            genx_key=genx_key,
            qwen_key=qwen_key,
            hf_token=hf_token,
            openai_key=openai_key,
        )

    async def _call_genx(self, prompt: str, max_tokens: int = 512) -> dict[str, Any] | None:
        if not self._genx_key:
            return None
        result = await self._genx.generate_text(
            prompt,
            system=(
                "You are an expert social media content creator. "
                "Your job is to write content that markets a specific business. "
                "Always keep content grounded to the business name, industry, and products/services provided. "
                "Never mention Amarktai, AmarktAI, or AI tool names unless the business itself is Amarktai. "
                "Hashtags must reflect the business industry and audience, not the AI platform."
            ),
            task="copy",
            max_tokens=max_tokens,
        )
        if not result:
            return None
        return {
            "text": result["text"],
            "model": result["model"],
            "tokens": result.get("tokens", 0),
            "provider": "genx",
            "cost_usd": result.get("cost_usd", 0.0),
        }

    # ------------------------------------------------------------------
    # Low-level provider calls
    # ------------------------------------------------------------------

    async def _call_amarktai_network(self, prompt: str, max_tokens: int = 512) -> dict[str, Any] | None:
        """
        Route through the AmarktAI Network super brain (top-priority provider).
        Only used when integration is enabled with a valid token and dashboard URL.
        Returns {text, model, tokens, provider, cost_usd} or None.
        """
        if not (
            settings.AMARKTAI_INTEGRATION_ENABLED
            and settings.AMARKTAI_DASHBOARD_URL
            and settings.AMARKTAI_INTEGRATION_TOKEN
        ):
            return None
        import httpx
        try:
            url = f"{settings.AMARKTAI_DASHBOARD_URL.rstrip('/')}/integrations/ai/generate"
            headers = {
                "Authorization": f"Bearer {settings.AMARKTAI_INTEGRATION_TOKEN}",
                "Content-Type": "application/json",
                "X-App-ID": settings.APP_ID,
                "X-App-Slug": settings.APP_SLUG,
            }
            payload = {
                "app_id": settings.APP_ID,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "capability": "reasoning",
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.debug("AmarktAI Network returned %s", resp.status_code)
                return None
            data = resp.json()
            text = data.get("text") or data.get("output", {}).get("text", "")
            if text:
                return {
                    "text": text,
                    "model": data.get("model", "amarktai-brain"),
                    "tokens": data.get("tokens_used", 0),
                    "provider": "amarktai_network",
                    "cost_usd": data.get("cost_usd", 0.0),
                }
        except Exception as exc:
            logger.debug("AmarktAI Network call failed: %s", exc)
        return None

    async def _call_qwen(self, prompt: str, max_tokens: int = 512) -> dict[str, Any] | None:
        """Call Qwen via DashScope API. Returns {text, model, tokens} or None."""
        if not self._qwen_key:
            return None
        import httpx
        headers = {
            "Authorization": f"Bearer {self._qwen_key}",
            "Content-Type": "application/json",
        }
        for model in ("qwen-turbo", "qwen-plus"):
            try:
                payload = {
                    "model": model,
                    "input": {
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    "parameters": {"max_tokens": max_tokens, "result_format": "message"},
                }
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(_DASHSCOPE_URL, headers=headers, json=payload)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                text = (
                    data.get("output", {})
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if text:
                    usage = data.get("usage", {})
                    return {
                        "text": text,
                        "model": model,
                        "tokens": usage.get("total_tokens", 0),
                        "provider": "qwen",
                        "cost_usd": round(usage.get("total_tokens", 0) * 0.0000002, 6),
                    }
            except Exception as exc:
                logger.debug("Qwen %s call failed: %s", model, exc)
        return None

    async def _call_huggingface(self, prompt: str, max_tokens: int = 512) -> dict[str, Any] | None:
        """Call HuggingFace Inference API. Returns {text, model, tokens} or None."""
        if not self._hf_token:
            return None
        import httpx
        headers = {"Authorization": f"Bearer {self._hf_token}"}
        for model in (_HF_DEFAULT_MODEL, _HF_FALLBACK_MODEL):
            try:
                url = _HF_INFERENCE_URL.format(model=model)
                payload = {
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": max_tokens, "return_full_text": False},
                }
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if isinstance(data, list) and data:
                    text = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    text = data.get("generated_text", "")
                else:
                    continue
                if text:
                    return {
                        "text": text,
                        "model": model,
                        "tokens": len(prompt.split()) + len(text.split()),
                        "provider": "huggingface",
                        "cost_usd": 0.0,
                    }
            except Exception as exc:
                logger.debug("HuggingFace %s call failed: %s", model, exc)
        return None

    async def _call_openai(self, prompt: str, max_tokens: int = 512) -> dict[str, Any] | None:
        """Call OpenAI gpt-3.5-turbo. Returns {text, model, tokens} or None."""
        if not self._openai_key:
            return None
        import httpx
        try:
            headers = {
                "Authorization": f"Bearer {self._openai_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": _OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            return {
                "text": text,
                "model": _OPENAI_MODEL,
                "tokens": tokens,
                "provider": "openai",
                "cost_usd": round(tokens * 0.000002, 6),
            }
        except Exception as exc:
            logger.debug("OpenAI call failed: %s", exc)
            return None

    async def _call_gemini(self, prompt: str, max_tokens: int = 512) -> dict[str, Any] | None:
        """Call Google Gemini. Returns {text, model, tokens} or None."""
        if not self._gemini_key:
            return None
        import httpx
        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{_GEMINI_MODEL}:generateContent?key={self._gemini_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            if text:
                return {
                    "text": text,
                    "model": _GEMINI_MODEL,
                    "tokens": len(prompt.split()) + len(text.split()),
                    "provider": "gemini",
                    "cost_usd": 0.0,
                }
            return None
        except Exception as exc:
            logger.debug("Gemini call failed: %s", exc)
            return None

    async def _generate_raw(self, prompt: str, max_tokens: int = 512) -> dict[str, Any]:
        """
        Walk the provider chain and return {text, provider, model, tokens_used, cost_usd}.
        Always returns a result — never raises.
        """
        for call in (
            self._call_amarktai_network,
            self._call_genx,
            self._call_qwen,
            self._call_huggingface,
            self._call_openai,
            self._call_gemini,
        ):
            try:
                result = await call(prompt, max_tokens)
                if result and result.get("text"):
                    return {
                        "text": result["text"],
                        "provider": result["provider"],
                        "model": result["model"],
                        "tokens_used": result.get("tokens", 0),
                        "cost_usd": result.get("cost_usd", 0.0),
                    }
            except Exception as exc:
                logger.warning("Provider call %s raised unexpectedly: %s", call.__name__, exc)

        # Template fallback — last resort
        logger.warning("All AI providers failed. Using template fallback.")
        return {
            "text": "",
            "provider": "template",
            "model": "template",
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

    # ------------------------------------------------------------------
    # Public API — content generation
    # ------------------------------------------------------------------

    async def generate_content(
        self,
        webapp_data: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
        """
        Generate platform-optimised social media content.

        Returns::

            {
                "title": str,
                "caption": str,
                "hashtags": list[str],
                "provider": str,
                "model": str,
                "tokens_used": int,
                "cost_usd": float,
                "_provider_tag": "ai" | "template",
            }
        """
        # Try delegating to the specialist HF generator first when GenX is not configured.
        if (self._qwen_key or self._hf_token) and not self._genx_key:
            try:
                from app.services.hf_generator import HuggingFaceGenerator
                gen = HuggingFaceGenerator(
                    hf_token=self._hf_token,
                    qwen_key=self._qwen_key,
                )
                result = await gen.generate_content(webapp_data, platform)
                if result and not result.get("_generation_error"):
                    result.setdefault("provider", "qwen" if self._qwen_key else "huggingface")
                    result.setdefault("model", "qwen-turbo")
                    result.setdefault("tokens_used", 0)
                    result.setdefault("cost_usd", 0.0)
                    result["_provider_tag"] = "ai"
                    return result
            except Exception as exc:
                logger.warning("HuggingFaceGenerator.generate_content failed: %s", exc)

        # Fallback: build a business-specific prompt and call provider chain
        name = webapp_data.get("name", "our business")
        description = webapp_data.get("description", "")
        category = webapp_data.get("category", "")
        target_audience = webapp_data.get("target_audience", "")
        products_services = webapp_data.get("products_services") or webapp_data.get("key_features") or []
        if isinstance(products_services, list):
            products_str = ", ".join(str(p) for p in products_services[:3]) if products_services else ""
        else:
            products_str = str(products_services)
        market_location = webapp_data.get("market_location", "")
        brand_voice = webapp_data.get("brand_voice", "")
        keywords = webapp_data.get("keywords") or []
        keywords_str = ", ".join(str(k) for k in keywords[:8]) if keywords else ""

        location_line = f" Market: {market_location}." if market_location else ""
        voice_line = f" Brand voice: {brand_voice}." if brand_voice else ""
        products_line = f" Products/services: {products_str}." if products_str else ""
        audience_line = f" Target audience: {target_audience}." if target_audience else ""
        category_line = f" Industry/category: {category}." if category else ""
        keywords_line = f" Keywords for hashtags: {keywords_str}." if keywords_str else ""

        prompt = (
            f"Write a short {platform} social media post for the following business. "
            f"Business name: {name}. "
            f"Description: {description}.{category_line}{products_line}{audience_line}{location_line}{voice_line}{keywords_line} "
            f"IMPORTANT: Market {name} specifically. Do NOT mention Amarktai or AmarktAI unless {name} is Amarktai. "
            f"Use hashtags relevant to {name}, its industry ({category or 'business'}), and its products/services. "
            f"Do NOT use generic system hashtags like #Amarktai, #AmarktaiMarketing, or #AIContent. "
            f"Make the content specific and authentic to {name}."
        )
        raw = await self._generate_raw(prompt, max_tokens=300)
        text = raw["text"]

        if raw["provider"] == "template" or not text:
            from app.services.hf_generator import HuggingFaceGenerator
            fallback = HuggingFaceGenerator._fallback_content(webapp_data, platform)
            fallback["provider"] = "template"
            fallback["model"] = "template"
            fallback["tokens_used"] = 0
            fallback["cost_usd"] = 0.0
            fallback["_provider_tag"] = "template"
            return fallback

        # Parse hashtags from generated text
        import re
        hashtags = re.findall(r"#\w+", text)
        caption = re.sub(r"#\w+", "", text).strip()

        return {
            "title": f"{name} on {platform.title()}",
            "caption": caption[:500],
            "hashtags": hashtags[:15],
            "provider": raw["provider"],
            "model": raw["model"],
            "tokens_used": raw["tokens_used"],
            "cost_usd": raw["cost_usd"],
            "_provider_tag": "ai",
        }

    async def generate_batch(
        self,
        webapp_data: dict[str, Any],
        platforms: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Generate content for multiple platforms."""
        results: dict[str, dict[str, Any]] = {}
        for platform in platforms:
            results[platform] = await self.generate_content(webapp_data, platform)
        return results

    async def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate free-form text using the best available provider.
        Returns the generated text string, or an empty string on failure.
        """
        raw = await self._generate_raw(prompt, max_tokens)
        return raw.get("text", "")

    async def summarize(self, text: str) -> str:
        """Summarise text using the best available provider."""
        if self._hf_token:
            try:
                from app.services.hf_generator import HuggingFaceGenerator
                gen = HuggingFaceGenerator(hf_token=self._hf_token, qwen_key=self._qwen_key)
                return await gen.summarize(text)
            except Exception:
                pass
        return text[:500]

    async def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Analyse sentiment of text."""
        if self._hf_token:
            try:
                from app.services.hf_generator import HuggingFaceGenerator
                gen = HuggingFaceGenerator(hf_token=self._hf_token, qwen_key=self._qwen_key)
                return await gen.analyze_sentiment(text)
            except Exception:
                pass
        return {"label": "NEUTRAL", "score": 0.5}

    async def classify_topics(self, text: str, labels: list[str]) -> dict[str, Any]:
        """Zero-shot topic classification."""
        if self._hf_token:
            try:
                from app.services.hf_generator import HuggingFaceGenerator
                gen = HuggingFaceGenerator(hf_token=self._hf_token, qwen_key=self._qwen_key)
                return await gen.classify_topics(text, labels)
            except Exception:
                pass
        return {"labels": labels, "scores": [1.0 / len(labels)] * len(labels)}

    async def extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        if self._hf_token:
            try:
                from app.services.hf_generator import HuggingFaceGenerator
                gen = HuggingFaceGenerator(hf_token=self._hf_token, qwen_key=self._qwen_key)
                return await gen.extract_keywords(text)
            except Exception:
                pass
        words = [w.strip(".,!?") for w in text.split() if len(w) > 4]
        return list(dict.fromkeys(words))[:10]
