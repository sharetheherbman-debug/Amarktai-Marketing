from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class GenXRouterClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.GENX_API_KEY
        self.base_url = (base_url or "https://query.genx.sh").rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def models(self, category: str | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "models": [], "error": "GenX not configured"}
        url = f"{self.base_url}/api/v1/models"
        params = {"category": category} if category else None
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code >= 400:
            return {"ok": False, "models": [], "error": f"HTTP {response.status_code}"}
        data = response.json()
        return {"ok": True, "models": data.get("data") or data.get("models") or data}

    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/api/v1/generate", headers=self._headers(), json=payload)
        return {"ok": response.status_code < 400, "status_code": response.status_code, "data": response.json()}

    async def job(self, job_id: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/api/v1/jobs/{job_id}", headers=self._headers())
        return {"ok": response.status_code < 400, "status_code": response.status_code, "data": response.json()}
