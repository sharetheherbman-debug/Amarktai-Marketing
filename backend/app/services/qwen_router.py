from __future__ import annotations

from typing import Any

from app.services.qwen_model_catalog import qwen_model_catalog


def route_qwen_model(capability: str, budget_mode: str = "budget") -> dict[str, Any]:
    catalog = qwen_model_catalog()["by_capability"]
    capability_key = capability if capability in catalog else "text"
    models = catalog.get(capability_key, [])
    if not models:
        return {"provider": "qwen", "model": None, "capability": capability_key}
    if budget_mode in {"budget", "auto"}:
        model = next((item for item in models if "flash" in item), models[0])
    elif budget_mode == "premium":
        model = next((item for item in models if "max" in item or "pro" in item), models[0])
    else:
        model = models[0]
    return {"provider": "qwen", "model": model, "capability": capability_key}
