from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter()


@router.get("/status")
async def worker_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    scheduler_active = bool(settings.ENABLE_AUTO_POST)
    learning_active = bool(settings.REDIS_URL)
    media_polling_active = bool(settings.GENX_API_KEY or settings.QWEN_API_KEY or settings.HUGGINGFACE_TOKEN)
    overall_mode = "automatic" if scheduler_active and learning_active else "manual"
    return {
        "mode": overall_mode,
        "message": (
            "Automatic publishing worker active."
            if scheduler_active
            else "Manual scheduling/planning active. Automatic publishing worker not configured."
        ),
        "workers": {
            "scheduler_publisher": {
                "configured": scheduler_active,
                "status": "active" if scheduler_active else "manual_mode",
            },
            "daily_learning": {
                "configured": learning_active,
                "status": "active" if learning_active else "manual_mode",
            },
            "media_polling": {
                "configured": media_polling_active,
                "status": "active" if media_polling_active else "manual_mode",
            },
            "retry_queue": {
                "configured": learning_active,
                "status": "active" if learning_active else "manual_mode",
            },
        },
    }
