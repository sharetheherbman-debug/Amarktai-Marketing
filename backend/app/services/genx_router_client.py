from __future__ import annotations

import asyncio
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

    async def list_models(self, category: str | None = None) -> dict[str, Any]:
        return await self.models(category=category)

    async def models(self, category: str | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "models": [], "error": "GenX not configured"}
        url = f"{self.base_url}/api/v1/models"
        params = {"category": category} if category else None
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, headers=self._headers(), params=params)
            if response.status_code >= 400:
                return {"ok": False, "models": [], "error": f"HTTP {response.status_code}"}
            data = response.json()
            return {"ok": True, "models": data.get("data") or data.get("models") or data}
        except Exception as exc:
            return {"ok": False, "models": [], "error": "GenX request failed"}

    async def get_model(self, model_id: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(f"{self.base_url}/api/v1/models/{model_id}", headers=self._headers())
            if response.status_code >= 400:
                return {"ok": False, "error": f"HTTP {response.status_code}"}
            return {"ok": True, "model": response.json()}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def create_generation_job(
        self,
        model: str,
        params: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.generate({"model": model, **(params or {}), "metadata": metadata or {}})

    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/generate", headers=self._headers(), json=payload
                )
            return {"ok": response.status_code < 400, "status_code": response.status_code, "data": response.json()}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self.job(job_id)

    async def job(self, job_id: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(f"{self.base_url}/api/v1/jobs/{job_id}", headers=self._headers())
            return {"ok": response.status_code < 400, "status_code": response.status_code, "data": response.json()}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def poll_job(
        self,
        job_id: str,
        timeout_seconds: int = 120,
        interval_seconds: int = 3,
    ) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        elapsed = 0
        while elapsed < timeout_seconds:
            result = await self.job(job_id)
            if not result.get("ok"):
                return result
            status = (result.get("data") or {}).get("status", "")
            if status in {"completed", "failed", "cancelled"}:
                return result
            await asyncio.sleep(interval_seconds)
            elapsed += interval_seconds
        return {"ok": False, "error": f"Job {job_id} polling timed out after {timeout_seconds}s"}

    async def get_job_result(self, job_id: str) -> dict[str, Any]:
        result = await self.job(job_id)
        if not result.get("ok"):
            return result
        data = result.get("data") or {}
        return {"ok": True, "job_id": job_id, "result": data.get("result"), "output": data.get("output"), "data": data}

    async def download_job_file(self, job_id: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        result = await self.job(job_id)
        data = (result.get("data") or {})
        output_url = data.get("result_url") or data.get("output_url") or data.get("url")
        if not output_url:
            return {"ok": False, "error": "No output URL available for this job"}
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(output_url, headers=self._headers())
            return {"ok": response.status_code < 400, "content": response.content, "content_type": response.headers.get("content-type", "")}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{self.base_url}/api/v1/jobs/{job_id}/cancel", headers=self._headers())
            return {"ok": response.status_code < 400, "status_code": response.status_code, "data": response.json()}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def get_credits(self) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(f"{self.base_url}/api/v1/credits", headers=self._headers())
            if response.status_code >= 400:
                return {"ok": False, "error": f"HTTP {response.status_code}"}
            return {"ok": True, "credits": response.json()}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def get_pricing(self, category: str | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "GenX not configured"}
        params = {"category": category} if category else None
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(f"{self.base_url}/api/v1/pricing", headers=self._headers(), params=params)
            if response.status_code >= 400:
                return {"ok": False, "error": f"HTTP {response.status_code}"}
            return {"ok": True, "pricing": response.json()}
        except Exception as exc:
            return {"ok": False, "error": "GenX request failed"}

    async def test_capability(
        self,
        category: str,
        model: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "configured": False, "error": "GenX not configured — add GENX_API_KEY"}
        test_prompt = prompt or f"Test {category} generation. Return a short sample."
        payload: dict[str, Any] = {"category": category, "prompt": test_prompt}
        if model:
            payload["model"] = model
        result = await self.generate(payload)
        return {
            "ok": result.get("ok", False),
            "configured": True,
            "category": category,
            "model": model,
            "result": result,
        }
