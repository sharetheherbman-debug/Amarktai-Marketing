from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.platform_intelligence import get_platform_intelligence, review_content

router = APIRouter()


class PlatformReviewRequest(BaseModel):
    platform: str
    content: str
    business_type: str | None = None


@router.get("")
async def platform_intelligence_index(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return get_platform_intelligence()


@router.get("/{platform}")
async def platform_intelligence_detail(
    platform: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload = get_platform_intelligence(platform)
    if payload.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Platform not found")
    return payload


@router.post("/review-content")
async def platform_review_content(
    payload: PlatformReviewRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return review_content(platform=payload.platform, content=payload.content, business_type=payload.business_type)
