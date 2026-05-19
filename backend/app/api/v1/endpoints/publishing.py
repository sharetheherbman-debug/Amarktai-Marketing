from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.content import Content, ContentStatus
from app.models.user import User
from app.models.user_api_key import UserIntegration
from app.services.posting_readiness import normalize_platform, platform_posting_state, publishing_readiness
from app.services.posting_service import post_to_platform

router = APIRouter()


class PostNowRequest(BaseModel):
    content_id: str
    platform: str | None = None


class TestPlatformRequest(BaseModel):
    platform: str


def _integration_payload(integration: UserIntegration | None) -> dict[str, Any]:
    if not integration or not integration.platform_data:
        return {}
    try:
        value = json.loads(integration.platform_data)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _is_low_risk(content: Content) -> bool:
    meta = content.generation_metadata or {}
    compliance = meta.get("compliance") if isinstance(meta, dict) else {}
    if isinstance(compliance, dict):
        risk = str(compliance.get("risk_level", "")).lower()
        if risk:
            return risk == "low"
    return not bool(meta.get("human_review_required")) if isinstance(meta, dict) else False


@router.get("/readiness")
async def get_publishing_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return publishing_readiness(db, current_user.id)


@router.post("/test-platform")
async def test_platform(
    payload: TestPlatformRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    state = platform_posting_state(db, current_user.id, payload.platform)
    return {
        "platform": state["platform"],
        "can_post_now": state["can_post_now"],
        "ui_status": state["ui_status"],
        "missing": state["missing"],
        "details": state,
    }


@router.post("/post-now")
async def post_now(
    payload: PostNowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = db.query(Content).filter(
        Content.id == payload.content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    platform = normalize_platform(payload.platform or content.platform)
    state = platform_posting_state(db, current_user.id, platform)
    if not state["posting_supported"]:
        raise HTTPException(status_code=409, detail=f"posting not implemented for {platform}")
    if not state["can_post_now"]:
        raise HTTPException(status_code=403, detail={"platform": platform, "missing": state["missing"], "status": state["ui_status"]})

    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.platform == platform,
    ).first()
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=403, detail="Platform is not connected")

    approved_or_auto = content.status == ContentStatus.APPROVED
    if not approved_or_auto:
        auto_post_enabled = bool(integration.auto_post_enabled)
        if not (auto_post_enabled and _is_low_risk(content)):
            raise HTTPException(status_code=403, detail="Human review required before posting")

    token = integration.get_access_token()
    payload_data = _integration_payload(integration)
    media_url = (content.media_urls or [None])[0] if isinstance(content.media_urls, list) else None

    credentials: dict[str, Any] = {}
    if platform == "facebook":
        credentials = {"page_access_token": token, "page_id": payload_data.get("page_id")}
    elif platform == "instagram":
        credentials = {"access_token": token, "ig_user_id": payload_data.get("ig_user_id")}
    elif platform == "linkedin":
        credentials = {"access_token": token, "person_urn": payload_data.get("person_urn")}
    elif platform == "reddit":
        credentials = {"access_token": token, "subreddit": payload_data.get("subreddit")}
    elif platform == "pinterest":
        credentials = {"access_token": token, "board_id": payload_data.get("board_id")}
    elif platform == "twitter":
        # Current integration flow is OAuth2; posting_service.twitter currently needs OAuth1 secrets.
        raise HTTPException(status_code=409, detail="posting not implemented for twitter current OAuth token shape")
    elif platform == "youtube":
        raise HTTPException(status_code=409, detail="posting not implemented for youtube current media upload flow")
    elif platform == "tiktok":
        raise HTTPException(status_code=409, detail="posting not implemented for tiktok current media upload flow")
    else:
        raise HTTPException(status_code=409, detail=f"posting not implemented for {platform}")

    try:
        result = await post_to_platform(
            platform=platform,
            credentials=credentials,
            message=content.caption,
            media_url=media_url,
            title=content.title,
            extra={
                "api_key": settings.TWITTER_API_KEY,
                "api_secret": settings.TWITTER_API_SECRET,
                "description": content.caption,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"post failed: {exc}")

    if not result.success:
        raise HTTPException(status_code=502, detail=result.error or "Platform rejected post")

    content.status = ContentStatus.POSTED
    content.posted_at = datetime.now(timezone.utc)
    content.platform_post_id = result.post_id
    db.commit()
    db.refresh(content)

    return {
        "ok": True,
        "content_id": content.id,
        "platform": platform,
        "post_id": result.post_id,
        "url": result.url,
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
    }
