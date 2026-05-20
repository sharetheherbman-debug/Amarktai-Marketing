from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class PixabayClient:
    def __init__(self, api_key: str, timeout: int = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "status": "missing_key", "error": "PIXABAY_API_KEY is missing.", "items": []}
        merged = {"key": self.api_key, **params}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=merged)
            if response.status_code in {400, 401, 403}:
                return {"ok": False, "status": "provider_rejected_key", "error": f"HTTP {response.status_code}", "items": []}
            if response.status_code >= 500:
                return {"ok": False, "status": "endpoint_unreachable", "error": f"HTTP {response.status_code}", "items": []}
            if response.status_code >= 400:
                return {"ok": False, "status": "provider_error", "error": f"HTTP {response.status_code}", "items": []}
            payload = response.json()
            items = payload.get("hits") if isinstance(payload, dict) else []
            return {"ok": True, "status": "test_passed", "error": None, "items": items or [], "total": payload.get("totalHits", 0)}
        except Exception:
            return {"ok": False, "status": "endpoint_unreachable", "error": "Pixabay request failed.", "items": []}

    async def search_images(self, **params: Any) -> dict[str, Any]:
        return await self._get("https://pixabay.com/api/", params)

    async def search_videos(self, **params: Any) -> dict[str, Any]:
        return await self._get("https://pixabay.com/api/videos/", params)
