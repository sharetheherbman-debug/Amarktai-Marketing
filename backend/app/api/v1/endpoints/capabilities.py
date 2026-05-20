from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.capability_catalog import build_capability_catalog
from app.services.provider_decision_engine import decide_provider
from app.services.provider_catalog import mask_value
from app.services.qwen_model_catalog import qwen_model_catalog
from app.api.v1.endpoints.settings import _resolve_provider_key, get_readiness

router = APIRouter()


class CapabilityRouteRequest(BaseModel):
    capability: str
    platform: str
    format: str = "text_post"
    business: dict[str, Any] | None = None
    budget_mode: str = "auto"


@router.get("")
async def get_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    readiness = await get_readiness(current_user=current_user, db=db)
    providers = {}
    for key in ["GENX_API_KEY", "FIRECRAWL_API_KEY", "QWEN_API_KEY", "HUGGINGFACE_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
        value, source = _resolve_provider_key(db, current_user.id, key, getattr(settings, key, "") or "")
        providers[key] = {"effective_source": source, "masked_value": mask_value(value)}
    catalog = build_capability_catalog(
        provider_resolution={"providers": providers},
        readiness=readiness,
        implemented_services={"website_scrape", "business_intelligence", "campaign_strategy", "platform_copy", "hashtags", "image_prompt", "video_script", "short_video_brief", "youtube_video_kit", "tiktok_reels_kit", "voiceover_script", "talking_avatar_script", "content_calendar", "schedule_planning", "performance_learning"},
    )
    return {"capabilities": catalog}


@router.post("/route")
async def route_capability(
    payload: CapabilityRouteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    provider_keys = {}
    for key in ["GENX_API_KEY", "QWEN_API_KEY", "HUGGINGFACE_TOKEN"]:
        value, _ = _resolve_provider_key(db, current_user.id, key, getattr(settings, key, "") or "")
        provider_keys[key.replace("_API_KEY", "").replace("_TOKEN", "").lower()] = bool(value)
    decision = decide_provider(
        capability=payload.capability,
        platform=payload.platform,
        fmt=payload.format,
        business=payload.business,
        budget_mode=payload.budget_mode.lower(),
        provider_keys=provider_keys,
        genx_catalog={},
        qwen_catalog=qwen_model_catalog(),
        hf_tasks={},
        platform_intelligence={},
        learning_insights={},
    )
    return {
        "selected_provider": decision["provider"],
        "selected_model": decision["model"],
        "fallback_chain": decision["fallback_chain"],
        "reason": decision["reason"],
    }
