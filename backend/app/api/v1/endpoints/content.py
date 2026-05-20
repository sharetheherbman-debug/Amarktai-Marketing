"""
Content endpoints — generate, approve, reject, manage social media content.

AI generation uses a tiered provider stack (primary → fallback → template).
Template-based generation is always available as a guaranteed fallback.

Rejecting a post marks it as rejected (safe state) and optionally queues
regeneration for the same webapp/platform in the background.

A rejection can NEVER break the content library, dashboard, or login.

Designed and created by AmarktAI Marketing
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from difflib import SequenceMatcher
from pydantic import BaseModel, Field

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, enforce_content_quota
from app.core.config import settings
from app.db.base import get_db
from app.models.content import Content as ContentModel, ContentStatus
from app.models.user import User
from app.schemas.content import Content, ContentUpdate
from app.services.social_rules import get_social_rule, resolve_platform_key
from app.services.provider_catalog import resolve_user_api_key
from app.services.business_intelligence import analyze_business
from app.services.platform_catalog import all_platforms, filter_launch_platforms, launch_platforms, normalize_platform as normalize_catalog_platform
from app.services.scheduler_runtime import upsert_scheduler_item
from app.models.marketing_runtime import SchedulerMode

logger = logging.getLogger(__name__)

router = APIRouter()

# Hashtags that should never appear in generated content unless the business
# itself is Amarktai or the user explicitly requests them.
_BANNED_SYSTEM_HASHTAGS = {"#amarktai", "#amarktaimarketing", "#aicontent"}


class GenerateAllRequest(BaseModel):
    webapp_id: str | None = None
    platforms: list[str] | None = None


class GenerateCreativeRequest(BaseModel):
    webapp_id: str
    platform: str
    format: str = "text_post"
    objective: str | None = None
    tone: str | None = None
    audience: str | None = None
    offer: str | None = None
    product_focus: str | None = None
    auto_select_format: bool = True


class GeneratePackRequest(BaseModel):
    webapp_id: str
    platforms: list[str] = list(all_platforms())
    objective: str | None = None
    tone: str | None = None
    audience: str | None = None
    offer: str | None = None
    product_focus: str | None = None
    formats: list[str] = ["text_post", "image_prompt", "video_script", "thumbnail_prompt", "talking_avatar_script", "voiceover_script"]
    auto_select_formats: bool = True


class ScheduleContentRequest(BaseModel):
    scheduled_for: str | None = None


class ImproveContentRequest(BaseModel):
    objective: str | None = None
    tone: str | None = None
    audience: str | None = None
    offer: str | None = None
    product_focus: str | None = None


class RegenerateContentRequest(BaseModel):
    feedback: str | None = None
    avoid_previous_text: list[str] = Field(default_factory=list)
    variation_seed: str | None = None


class RejectItemRequest(BaseModel):
    reason: str | None = None
    feedback: str | None = None
    regenerate: bool = False


def _extract_intelligence(webapp) -> dict:
    if isinstance(webapp.scraped_data, dict):
        return webapp.scraped_data
    return {}


def _filter_hashtags(hashtags: list, business_name: str = "") -> list:
    """Remove banned system hashtags unless they belong to the business itself."""
    bn_lower = (business_name or "").lower()
    is_amarktai_business = "amarktai" in bn_lower
    result = []
    for tag in hashtags:
        if tag.lower() in _BANNED_SYSTEM_HASHTAGS and not is_amarktai_business:
            continue
        result.append(tag)
    return result


def _template_from_intelligence(webapp_data: dict, platform: str, *, objective: str | None = None, tone: str | None = None, include_hashtags: bool = True, include_cta: bool = True) -> dict:
    name = webapp_data.get("name") or "Your Business"
    summary = webapp_data.get("summary") or webapp_data.get("description") or f"{name} helps customers solve important problems."
    audience = webapp_data.get("target_audience") or "people interested in your offering"
    products = webapp_data.get("products_services") or webapp_data.get("key_features") or []
    product_line = ", ".join(products[:3]) if isinstance(products, list) and products else "our core services"
    objective_line = f" Objective: {objective}." if objective else ""
    tone_line = f" Tone: {tone}." if tone else ""
    cta = "Learn more at our website" if include_cta else ""
    caption = (
        f"{name} on {platform.title()}: {summary} "
        f"We focus on {product_line} for {audience}.{objective_line}{tone_line} {cta}"
    ).strip()
    hashtags = []
    if include_hashtags:
        raw_tags = [f"#{tag}" for tag in (webapp_data.get("keywords") or [])[:6]]
        hashtags = _filter_hashtags(raw_tags, business_name=name)
    return {
        "title": f"{name} • {platform.title()}",
        "caption": caption[:1000],
        "hashtags": hashtags,
    }


def _get_hf_token(db: Session, user: User) -> str | None:
    from app.core.config import settings
    return resolve_user_api_key(db, user.id, "HUGGINGFACE_TOKEN", settings.HUGGINGFACE_TOKEN) or None


def _get_qwen_key(db: Session, user: User) -> str | None:
    from app.core.config import settings
    return resolve_user_api_key(db, user.id, "QWEN_API_KEY", settings.QWEN_API_KEY) or None


def _get_openai_key(db: Session, user: User) -> str | None:
    from app.core.config import settings
    return resolve_user_api_key(db, user.id, "OPENAI_API_KEY", settings.OPENAI_API_KEY) or None


def _get_genx_key(db: Session, user: User) -> str | None:
    from app.core.config import settings
    return resolve_user_api_key(db, user.id, "GENX_API_KEY", settings.GENX_API_KEY) or None


def _get_firecrawl_key(db: Session, user: User) -> str | None:
    from app.core.config import settings
    return resolve_user_api_key(db, user.id, "FIRECRAWL_API_KEY", settings.FIRECRAWL_API_KEY) or None


async def _generate_text_content(
    webapp_data: dict,
    platform: str,
    hf_token: str | None,
    openai_key: str | None,
    qwen_key: str | None = None,
    genx_key: str | None = None,
) -> dict:
    """Unified AI provider chain with GenX-first routing and template fallback."""
    from app.services.ai_provider import AIProvider
    from app.services.hf_generator import HuggingFaceGenerator

    provider = AIProvider.from_keys(
        genx_key=genx_key or "",
        qwen_key=qwen_key or "",
        hf_token=hf_token or "",
        openai_key=openai_key or "",
    )
    try:
        result = await provider.generate_content(webapp_data, platform)
        if result and result.get("caption"):
            return result
    except Exception:
        pass
    return HuggingFaceGenerator._fallback_content(webapp_data, platform)


def _compliance_for(platform: str, caption: str) -> dict:
    rule = get_social_rule(resolve_platform_key(platform))
    text = (caption or "").lower()
    high_risk_terms = ["guaranteed", "cure", "financial advice", "get rich", "medical advice", "legal advice"]
    flagged = [term for term in high_risk_terms if term in text]
    review_required = bool(flagged)
    risk_level = "high" if flagged else "low"
    return {
        "risk_level": risk_level,
        "flags": flagged,
        "notes": (rule.compliance_notes if rule else []),
        "summary": (
            f"Human review required due to risky claims: {', '.join(flagged)}"
            if flagged
            else "No high-risk terms detected; conservative policy checks passed."
        ),
        "human_review_required": review_required,
    }


def _generation_package(platform: str, result: dict, provider_name: str, generation_status: str, generation_message: str, genx_configured: bool) -> dict:
    caption = result.get("caption", "")
    compliance = _compliance_for(platform, caption)
    hashtags = result.get("hashtags", [])
    hook = caption.split("\n", 1)[0][:120] if caption else ""
    cta = "Learn more" if "http" in caption else "Tell us what you think"
    suggested_post_time = (get_social_rule(resolve_platform_key(platform)).best_times_b2c[0] if get_social_rule(resolve_platform_key(platform)) else "Wed 12:00")
    return {
        "ai_generated": provider_name != "template",
        "generation_status": generation_status,
        "provider": provider_name,
        "model": result.get("model", ""),
        "message": generation_message,
        "requires": [] if genx_configured else ["GENX_API_KEY"],
        "hook": hook,
        "cta": cta,
        "hashtags": hashtags,
        "suggested_post_time": suggested_post_time,
        "compliance": compliance,
        "compliance_flags": compliance["flags"],
        "human_review_required": compliance["human_review_required"],
    }


def _truthful_generation_metadata(
    *,
    provider_attempted: str,
    provider_actual: str,
    model_attempted: str,
    model_actual: str,
    task_used: str,
    capability_used: str,
    generation_status: str,
    degraded: bool,
    reason: str,
    missing_capabilities: list[str],
    asset_generation_status: str,
    scrape_provider: str,
    scrape_status: str,
    platform_review: dict,
) -> dict:
    return {
        "provider_attempted": provider_attempted,
        "provider_actual": provider_actual,
        "model_attempted": model_attempted,
        "model_actual": model_actual,
        "task_used": task_used,
        "capability_used": capability_used,
        "generation_status": generation_status,
        "degraded": degraded,
        "reason": reason,
        "missing_capabilities": missing_capabilities,
        "asset_generation_status": asset_generation_status,
        "platform_fit_score": platform_review.get("platform_fit_score"),
        "algorithm_suggestions": platform_review.get("algorithm_fit_suggestions", []),
        "terms_policy_warnings": platform_review.get("terms_policy_warnings", []),
        "customer_conversion_suggestions": platform_review.get("customer_conversion_suggestions", []),
        "follower_growth_suggestions": platform_review.get("follower_growth_suggestions", []),
        "scrape_provider": scrape_provider,
        "scrape_status": scrape_status,
    }


def _content_type_for_format(fmt: str) -> str:
    if fmt in {"generated_image", "image_prompt", "thumbnail_prompt"}:
        return "image"
    if fmt in {"video_script", "short_video_brief", "youtube_video_kit", "tiktok_reels_kit", "talking_avatar_video"}:
        return "video"
    if fmt == "carousel":
        return "carousel"
    return "text"


def _safe_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _safe_str(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").strip().lower(), (b or "").strip().lower()).ratio()


def _build_preview_title(content: ContentModel, metadata: dict) -> str:
    if metadata.get("preview_title"):
        return str(metadata.get("preview_title"))
    return str(content.title or f"{content.platform.title()} draft")


def _build_preview_summary(content: ContentModel, metadata: dict) -> str:
    if metadata.get("preview_summary"):
        return str(metadata.get("preview_summary"))
    caption = str(content.caption or "")
    return caption[:220]


def _content_item_payload(content: ContentModel) -> dict:
    """Serialize a ContentModel row into the content library item dict.

    This function must NEVER raise.  Any field access uses safe defaults so that
    a malformed or partially-populated row does not crash the library endpoint.
    """
    try:
        metadata = content.generation_metadata or {}
    except Exception:
        metadata = {}

    try:
        status_val = content.status.value if hasattr(content.status, "value") else str(content.status or "")
    except Exception:
        status_val = "unknown"

    try:
        type_val = content.type.value if hasattr(content.type, "value") else str(content.type or "")
    except Exception:
        type_val = "text"

    # Status in content library: use the DB status field for accuracy
    db_status = status_val
    gen_status = metadata.get("generation_status", db_status)

    # Provenance fields
    source_route = metadata.get("source_route", "unknown")
    source_action = metadata.get("source_action", "unknown")
    business_snapshot = metadata.get("source_business_snapshot") or metadata.get("business_snapshot")
    business_name = _safe_str(
        (business_snapshot or {}).get("name") if isinstance(business_snapshot, dict) else None
    ) or metadata.get("business_name", "")
    rejection_reason = metadata.get("rejection_reason")

    return {
        "id": _safe_str(content.id),
        "user_id": _safe_str(content.user_id),
        "webapp_id": _safe_str(content.webapp_id),
        "business_name": business_name,
        "campaign_id": metadata.get("campaign_id"),
        "source_route": source_route,
        "source_action": source_action,
        "platform": _safe_str(content.platform),
        "format": metadata.get("format", type_val),
        "status": db_status,
        "title": _safe_str(content.title),
        "preview_title": _build_preview_title(content, metadata),
        "preview_summary": _build_preview_summary(content, metadata),
        "caption": _safe_str(content.caption),
        "body": _safe_str(content.caption),
        "hooks": _safe_list(metadata.get("hooks")),
        "hashtags": _safe_list(content.hashtags),
        "cta": metadata.get("cta"),
        "image_prompt": metadata.get("image_prompt"),
        "video_script": metadata.get("video_script"),
        "shot_list": _safe_list(metadata.get("shot_list")),
        "voiceover_script": metadata.get("voiceover_script"),
        "avatar_script": metadata.get("avatar_script"),
        "thumbnail_prompt": metadata.get("thumbnail_prompt"),
        "carousel_slides": _safe_list(metadata.get("carousel_slides")),
        "platform_fit_score": metadata.get("platform_fit_score"),
        "compliance_notes": _safe_list(metadata.get("terms_policy_warnings")) or _safe_list(metadata.get("compliance_flags")),
        "provider_attempted": metadata.get("provider_attempted"),
        "provider_actual": metadata.get("provider_actual"),
        "model_actual": metadata.get("model_actual") or metadata.get("model"),
        "provider_selected": metadata.get("provider_actual"),
        "model_selected": metadata.get("model_actual") or metadata.get("model"),
        "fallback_chain": _safe_list(metadata.get("fallback_chain")),
        "task_used": metadata.get("task_used"),
        "capability_used": metadata.get("capability_used"),
        "generated_by": metadata.get("provider_actual") or metadata.get("provider_attempted") or "template",
        "variation_seed": metadata.get("variation_seed"),
        "uniqueness_score": metadata.get("uniqueness_score"),
        "business_grounding_score": metadata.get("business_grounding_score"),
        "hashtag_relevance_score": metadata.get("hashtag_relevance_score"),
        "creative_relevance_score": metadata.get("creative_relevance_score"),
        "warnings": _safe_list(metadata.get("warnings")),
        "generation_status": gen_status,
        "degraded": bool(metadata.get("degraded")),
        "reason": metadata.get("reason"),
        "rejection_reason": rejection_reason,
        "asset_generation_status": metadata.get("asset_generation_status"),
        "media_job_ids": _safe_list(metadata.get("media_job_ids")),
        "media_asset_ids": _safe_list(metadata.get("media_asset_ids")),
        "media_urls": _safe_list(content.media_urls),
        "source_business_snapshot": business_snapshot,
        "parent_content_id": _safe_str(content.parent_content_id),
        "scheduler_item_id": metadata.get("scheduler_item_id"),
        "scheduled_for": content.scheduled_for,
        "scrape_snapshot": metadata.get("scrape_snapshot"),
        "prompt_hash": metadata.get("prompt_hash"),
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


@router.get("/", response_model=List[Content])
async def get_content(
    content_status: ContentStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("get_content called by user=%s status=%s", current_user.id, content_status)
    query = db.query(ContentModel).filter(ContentModel.user_id == current_user.id)
    if content_status:
        query = query.filter(ContentModel.status == content_status)
    return query.order_by(ContentModel.created_at.desc()).all()


@router.get("/items")
async def list_content_items(
    webapp_id: str | None = None,
    platform: str | None = None,
    fmt: str | None = Query(default=None, alias="format"),
    status: str | None = None,
    provider: str | None = None,
    date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("list_content_items user=%s webapp_id=%s status=%s", current_user.id, webapp_id, status)
    query = db.query(ContentModel).filter(ContentModel.user_id == current_user.id)
    if webapp_id:
        query = query.filter(ContentModel.webapp_id == webapp_id)
    if platform:
        query = query.filter(ContentModel.platform == normalize_catalog_platform(platform))
    rows = query.order_by(ContentModel.created_at.desc()).all()

    # Serialize each row safely — a bad row must not crash the whole list
    payload = []
    for item in rows:
        try:
            payload.append(_content_item_payload(item))
        except Exception as exc:
            row_id = getattr(item, "id", "?")
            logger.warning("Skipping malformed content row %s: %s", row_id, exc)
            payload.append({
                "id": row_id if isinstance(row_id, str) else "unknown",
                "platform": getattr(item, "platform", "unknown"),
                "generation_status": "error",
                "title": "Malformed content record",
                "caption": "",
                "body": "",
                "hashtags": [],
                "media_job_ids": [],
                "media_asset_ids": [],
                "media_urls": [],
                "degraded": True,
                "reason": "Content record could not be loaded. Contact support if this persists.",
            })

    if fmt:
        payload = [item for item in payload if str(item.get("format", "")).lower() == fmt.lower()]
    if status:
        # Filter by both DB status and generation_status for flexibility
        status_lower = status.lower()
        payload = [
            item for item in payload
            if str(item.get("status", "")).lower() == status_lower
            or str(item.get("generation_status", "")).lower() == status_lower
        ]
    if provider:
        payload = [item for item in payload if str(item.get("provider_actual", "")).lower() == provider.lower()]
    if date:
        payload = [item for item in payload if item.get("created_at") and str(item["created_at"]).startswith(date)]
    return payload


@router.get("/items/{content_id}")
async def get_content_item_details(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return _content_item_payload(content)


@router.get("/provenance")
async def get_content_provenance(
    webapp_id: str | None = None,
    source_action: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return provenance records for all content items — where each one came from."""
    query = db.query(ContentModel).filter(ContentModel.user_id == current_user.id)
    if webapp_id:
        query = query.filter(ContentModel.webapp_id == webapp_id)
    rows = query.order_by(ContentModel.created_at.desc()).all()
    result = []
    for item in rows:
        try:
            payload = _content_item_payload(item)
            if source_action and payload.get("source_action", "unknown") != source_action:
                continue
            if status:
                status_lower = status.lower()
                if str(payload.get("status", "")).lower() != status_lower and str(payload.get("generation_status", "")).lower() != status_lower:
                    continue
            if provider and str(payload.get("provider_actual", "")).lower() != provider.lower():
                continue
            if date and not str(payload.get("created_at", "")).startswith(date):
                continue
            result.append({
                "id": payload["id"],
                "webapp_id": payload["webapp_id"],
                "business_name": payload.get("business_name", ""),
                "platform": payload["platform"],
                "status": payload.get("status", ""),
                "source_route": payload.get("source_route", "unknown"),
                "source_action": payload.get("source_action", "unknown"),
                "generated_by": payload.get("generated_by", "template"),
                "provider_actual": payload.get("provider_actual"),
                "model_actual": payload.get("model_actual"),
                "rejection_reason": payload.get("rejection_reason"),
                "created_at": payload.get("created_at"),
            })
        except Exception as exc:
            logger.warning("Provenance row error for %s: %s", getattr(item, "id", "?"), exc)
    return result


@router.get("/webapp/{webapp_id}")
async def get_content_for_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(ContentModel)
        .filter(ContentModel.user_id == current_user.id, ContentModel.webapp_id == webapp_id)
        .order_by(ContentModel.created_at.desc())
        .all()
    )
    result = []
    for item in rows:
        try:
            result.append(_content_item_payload(item))
        except Exception as exc:
            logger.warning("Skipping malformed content row in webapp query %s: %s", getattr(item, "id", "?"), exc)
    return result


@router.delete("/items/{content_id}")
async def delete_content_item(
    content_id: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("delete_content_item user=%s id=%s confirm=%s", current_user.id, content_id, confirm)
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to delete this content item.")
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    db.delete(content)
    db.commit()
    logger.info("Deleted content item %s", content_id)
    return {"deleted": True, "id": content_id}


@router.post("/items/{content_id}/reject")
async def reject_content_item(
    content_id: str,
    payload: RejectItemRequest = Body(default_factory=RejectItemRequest),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a content item safely.

    - Sets status=rejected and stores reason/feedback in generation_metadata.
    - Rejected items remain visible under the 'rejected' filter — they are NOT deleted.
    - They feed into the learning/improve loop via rejection_reason.
    - If regenerate=True, a new improved item is created referencing this item
      as parent_item_id in its metadata.
    - Rejection can NEVER crash the dashboard, content library, or login.
    """
    logger.info(
        "reject_content_item user=%s id=%s reason=%s regenerate=%s",
        current_user.id, content_id, payload.reason, payload.regenerate,
    )
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Update status and store rejection context in metadata
    content.status = ContentStatus.REJECTED
    try:
        existing_metadata = dict(content.generation_metadata or {})
    except Exception:
        existing_metadata = {}
    existing_metadata["rejection_reason"] = payload.reason or ""
    existing_metadata["rejection_feedback"] = payload.feedback or ""
    content.generation_metadata = existing_metadata

    try:
        db.commit()
        db.refresh(content)
        logger.info("Content item %s set to rejected", content_id)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to set content %s to rejected: %s", content_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject content item.") from exc

    # Optionally queue regeneration (non-blocking — failure must not affect this response)
    if payload.regenerate:
        rejected_webapp_id = content.webapp_id
        rejected_platform = content.platform
        user_id = current_user.id

        async def _regen_after_rejection():
            from app.db.base import SessionLocal
            from app.models.webapp import WebApp
            from app.services.media_service import get_media_url, VIDEO_PLATFORMS
            regen_db = SessionLocal()
            try:
                regen_user = regen_db.query(User).filter(User.id == user_id).first()
                if not regen_user:
                    return
                webapp = regen_db.query(WebApp).filter(
                    WebApp.id == rejected_webapp_id, WebApp.user_id == user_id
                ).first()
                if not webapp:
                    return
                hf_token = _get_hf_token(regen_db, regen_user)
                qwen_key = _get_qwen_key(regen_db, regen_user)
                openai_key = _get_openai_key(regen_db, regen_user)
                genx_key = _get_genx_key(regen_db, regen_user)
                webapp_data = {
                    "name": webapp.name or "",
                    "url": str(webapp.url or ""),
                    "description": webapp.description or "",
                    "category": getattr(webapp, "category", "") or "",
                    "target_audience": getattr(webapp, "target_audience", "") or "",
                    "key_features": webapp.key_features or [],
                    "products_services": webapp.key_features or [],
                    "market_location": getattr(webapp, "market_location", "") or "",
                    "brand_voice": getattr(webapp, "brand_voice", "") or "",
                }
                result = await _generate_text_content(
                    webapp_data, rejected_platform, hf_token, openai_key, qwen_key, genx_key
                )
                media_urls = await get_media_url(rejected_platform, webapp_data, qwen_key or hf_token)
                content_type_val = "video" if rejected_platform in VIDEO_PLATFORMS else "image"
                generator_name = "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template"))
                new_content = ContentModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    webapp_id=rejected_webapp_id,
                    platform=rejected_platform,
                    type=content_type_val,
                    status=ContentStatus.PENDING,
                    title=result.get("title", "Regenerated Content"),
                    caption=result.get("caption", ""),
                    hashtags=_filter_hashtags(result.get("hashtags", []), business_name=webapp.name or ""),
                    media_urls=media_urls,
                    parent_content_id=content_id,
                    generation_metadata={
                        **_generation_package(
                            rejected_platform, result, generator_name,
                            "configured" if genx_key else "not_configured",
                            "Regenerated after rejection.",
                            bool(genx_key),
                        ),
                        "source_route": "/content/items/{id}/reject",
                        "source_action": "reject_regen",
                        "parent_item_id": content_id,
                        "rejection_reason": payload.reason or "",
                    },
                )
                regen_db.add(new_content)
                regen_db.commit()
                logger.info(
                    "Replacement item %s generated after rejection of %s on %s",
                    new_content.id, content_id, rejected_platform,
                )
            except Exception as exc:
                logger.error(
                    "Regen after rejection of %s failed: %s", content_id, exc, exc_info=True
                )
            finally:
                try:
                    regen_db.close()
                except Exception:
                    pass

        background_tasks.add_task(_regen_after_rejection)

    return _content_item_payload(content)


@router.post("/items/{content_id}/schedule")
async def schedule_content_item(
    content_id: str,
    payload: ScheduleContentRequest = Body(default_factory=ScheduleContentRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    scheduled_for = None
    if payload.scheduled_for:
        try:
            scheduled_for = datetime.fromisoformat(payload.scheduled_for.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="scheduled_for must be an ISO datetime.") from exc
    planned_at = scheduled_for or (datetime.now(timezone.utc) + timedelta(hours=1))
    item = upsert_scheduler_item(
        db,
        user_id=current_user.id,
        content=content,
        planned_at=planned_at,
        mode=SchedulerMode.MANUAL.value,
    )
    metadata = dict(content.generation_metadata or {})
    metadata["scheduler_item_id"] = item.id
    metadata["schedule_status"] = item.status
    content.generation_metadata = metadata
    db.commit()
    db.refresh(content)
    return _content_item_payload(content)


@router.post("/items/{content_id}/duplicate")
async def duplicate_content_item(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    duplicated = ContentModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        webapp_id=content.webapp_id,
        platform=content.platform,
        type=content.type,
        status=ContentStatus.PENDING,
        title=f"{content.title} (copy)",
        caption=content.caption,
        hashtags=content.hashtags or [],
        media_urls=content.media_urls or [],
        generation_metadata={
            **(content.generation_metadata or {}),
            "duplicated_from": content.id,
            "source_route": "/content/items/{id}/duplicate",
            "source_action": "duplicate",
        },
    )
    db.add(duplicated)
    db.commit()
    db.refresh(duplicated)
    return _content_item_payload(duplicated)


@router.post("/items/{content_id}/improve")
async def improve_content_item(
    content_id: str,
    payload: ImproveContentRequest = Body(default_factory=ImproveContentRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    improved = await generate_content(
        webapp_id=content.webapp_id,
        platform=content.platform,
        objective=payload.objective,
        tone=payload.tone,
        audience=payload.audience,
        product_focus=payload.product_focus or payload.offer or None,
        db=db,
        current_user=current_user,
    )
    metadata = dict(improved.generation_metadata or {})
    metadata["improved_from"] = content.id
    metadata["source_route"] = "/content/items/{id}/improve"
    metadata["source_action"] = "improve"
    improved.generation_metadata = metadata
    db.commit()
    db.refresh(improved)
    return _content_item_payload(improved)


@router.post("/items/{content_id}/regenerate")
async def regenerate_content_item(
    content_id: str,
    payload: RegenerateContentRequest = Body(default_factory=RegenerateContentRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id,
        ContentModel.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    prior_metadata = dict(content.generation_metadata or {})
    feedback = (payload.feedback or "").strip()
    improved = await generate_content(
        webapp_id=content.webapp_id,
        platform=content.platform,
        objective=feedback or None,
        db=db,
        current_user=current_user,
    )
    metadata = dict(improved.generation_metadata or {})
    avoid_list = [content.caption, *payload.avoid_previous_text]
    similarity = _similarity(improved.caption or "", content.caption or "")
    metadata.update(
        {
            "source_route": "/content/items/{id}/regenerate",
            "source_action": "regenerate",
            "improved_from": content.id,
            "parent_content_id": content.id,
            "rejection_feedback": feedback,
            "avoid_previous_text": [text for text in avoid_list if text][:8],
            "variation_seed": payload.variation_seed or str(uuid.uuid4()),
            "uniqueness_score": int(max(0, min(100, round((1 - similarity) * 100)))),
            "needs_review_duplicate": similarity >= 0.9,
            "warnings": list(metadata.get("warnings") or []) + (["Possible duplicate copy detected; adjust angle/CTA."] if similarity >= 0.9 else []),
            "fallback_chain": metadata.get("fallback_chain") or ["genx", "qwen", "huggingface", "template"],
            "preview_title": metadata.get("preview_title") or prior_metadata.get("preview_title") or improved.title,
            "preview_summary": (improved.caption or "")[:220],
        }
    )
    improved.generation_metadata = metadata
    improved.parent_content_id = content.id
    db.commit()
    db.refresh(improved)
    return _content_item_payload(improved)


@router.post("/preview")
async def preview_content_item(
    payload: GenerateCreativeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    generated = await generate_creative(payload=payload, db=db, current_user=current_user)
    content_id = generated.get("content_id")
    item = None
    if content_id:
        row = db.query(ContentModel).filter(ContentModel.id == content_id, ContentModel.user_id == current_user.id).first()
        if row:
            item = _content_item_payload(row)
    return {
        "status": "preview_ready",
        "content_id": content_id,
        "preview": item or generated,
    }


@router.post("/items/{content_id}/review-grounding")
async def review_item_grounding(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Score business grounding, creative relevance, and hashtag relevance for a content item."""
    from app.models.webapp import WebApp
    from app.services.creative_brief_builder import score_creative_relevance, _get_industry_rules

    content = db.query(ContentModel).filter(
        ContentModel.id == content_id, ContentModel.user_id == current_user.id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    metadata = content.generation_metadata or {}
    snapshot = metadata.get("source_business_snapshot") or {}

    if not snapshot:
        webapp = db.query(WebApp).filter(
            WebApp.id == content.webapp_id, WebApp.user_id == current_user.id
        ).first()
        if webapp:
            snapshot = {
                "id": webapp.id,
                "name": webapp.name or "",
                "category": getattr(webapp, "category", "") or "",
                "target_audience": getattr(webapp, "target_audience", "") or "",
                "products_services": webapp.key_features or [],
            }

    content_text = content.caption or ""
    image_prompt = metadata.get("image_prompt") or ""
    hashtags = _safe_list(content.hashtags)
    business_name = snapshot.get("name", "")
    category = snapshot.get("category", "")

    # Business grounding score
    grounding = score_creative_relevance(content_text, image_prompt, snapshot)

    # Hashtag relevance score
    banned_tags = {"#amarktai", "#amarktaimarketing", "#aicontent"}
    ht_lower = [h.lower() for h in hashtags]
    bad_hashtags = [h for h in ht_lower if h in banned_tags]
    bn_lower = business_name.lower()
    good_hashtags = [h for h in ht_lower if bn_lower and bn_lower.split()[0] in h] if bn_lower else []
    hashtag_score = 100
    if bad_hashtags:
        hashtag_score -= 30 * len(bad_hashtags)
    if not good_hashtags and hashtags:
        hashtag_score -= 10
    hashtag_score = max(0, hashtag_score)

    issues = list(grounding["issues"])
    if bad_hashtags:
        issues.append(f"Banned system hashtags detected: {bad_hashtags}")

    suggested_fix = []
    if grounding["creative_relevance_score"] < 70:
        suggested_fix.append(f"Regenerate content with explicit business context for '{business_name}'")
    if bad_hashtags:
        suggested_fix.append(f"Remove hashtags: {bad_hashtags} and replace with {category}-specific tags")

    return {
        "content_id": content_id,
        "business_grounding_score": grounding["creative_relevance_score"],
        "creative_relevance_score": grounding["creative_relevance_score"],
        "hashtag_relevance_score": hashtag_score,
        "needs_review": grounding["needs_review"] or hashtag_score < 70,
        "issues": issues,
        "suggested_fix": suggested_fix,
        "business_name": business_name,
        "category": category,
    }


@router.get("/pending", response_model=List[Content])
async def get_pending_content(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ContentModel)
        .filter(ContentModel.user_id == current_user.id, ContentModel.status == ContentStatus.PENDING)
        .order_by(ContentModel.created_at.desc())
        .all()
    )


@router.get("/{content_id}", response_model=Content)
async def get_content_item(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id, ContentModel.user_id == current_user.id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/generate")
async def generate_content(
    webapp_id: str,
    platform: str,
    objective: str | None = None,
    tone: str | None = None,
    campaign_type: str | None = None,
    product_focus: str | None = None,
    offer: str | None = None,
    audience: str | None = None,
    include_hashtags: bool = True,
    include_cta: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    """Generate AI content (text + image/video). Falls back to templates if no AI key configured."""
    from app.models.webapp import WebApp
    from app.services.media_service import get_media_url, VIDEO_PLATFORMS
    from app.services.business_grounding import build_business_grounding_context, score_business_grounding
    from app.services.hashtag_strategy import build_hashtag_strategy
    from app.services.content_quality_gate import evaluate_quality_gate

    platform = normalize_catalog_platform(platform)
    if platform not in launch_platforms():
        raise HTTPException(status_code=422, detail=f"Unsupported platform '{platform}'")

    webapp = db.query(WebApp).filter(WebApp.id == webapp_id, WebApp.user_id == current_user.id).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    hf_token = _get_hf_token(db, current_user)
    openai_key = _get_openai_key(db, current_user)
    qwen_key = _get_qwen_key(db, current_user)
    genx_key = _get_genx_key(db, current_user)
    firecrawl_key = _get_firecrawl_key(db, current_user)

    intelligence = _extract_intelligence(webapp)
    if webapp.url and not intelligence:
        try:
            intelligence = await analyze_business(
                url=webapp.url,
                name=webapp.name,
                description=webapp.description,
                firecrawl_api_key=firecrawl_key,
                timeout=25,
            )
            webapp.scraped_data = intelligence
            db.commit()
        except Exception:
            intelligence = {"scrape_status": "failed", "source_provider": "manual", "warnings": ["Website analysis failed; using manual profile data."]}

    webapp_data = {
        "name": webapp.name or intelligence.get("business_name") or "Business",
        "url": str(webapp.url or intelligence.get("normalized_url") or ""),
        "description": webapp.description or intelligence.get("page_summary") or "",
        "summary": intelligence.get("page_summary") or "",
        "category": webapp.category or "",
        "target_audience": audience or webapp.target_audience or intelligence.get("target_audience_guess") or "",
        "key_features": webapp.key_features or intelligence.get("products_services") or [],
        "products_services": intelligence.get("products_services") or webapp.key_features or [],
        "keywords": intelligence.get("keywords") or [],
        "market_location": getattr(webapp, "market_location", "") or "",
        "brand_voice": getattr(webapp, "brand_voice", "") or "",
        "social_links": intelligence.get("social_links") or [],
    }
    effective_product_focus = product_focus or offer or None
    if effective_product_focus:
        webapp_data["products_services"] = [effective_product_focus, *list(webapp_data.get("products_services") or [])][:5]
    if campaign_type:
        webapp_data["campaign_type"] = campaign_type
    if objective:
        webapp_data["objective"] = objective
    if tone:
        webapp_data["tone"] = tone
    grounding_context = build_business_grounding_context(webapp_data)
    webapp_data["description"] = f"{grounding_context['prompt_prefix']} {webapp_data['description']}".strip()

    # Snapshot of the business used at generation time (provenance)
    source_business_snapshot = {
        "id": webapp.id,
        "name": webapp.name or "",
        "url": str(webapp.url or ""),
        "description": webapp.description or "",
        "category": webapp.category or "",
        "target_audience": webapp_data["target_audience"],
        "products_services": webapp_data["products_services"],
        "market_location": webapp_data.get("market_location", ""),
        "brand_voice": webapp_data.get("brand_voice", ""),
    }

    generation_warnings = list(intelligence.get("warnings") or [])
    result = {}
    genx_failed = False
    try:
        result = await _generate_text_content(webapp_data, platform, hf_token, openai_key, qwen_key, genx_key)
    except Exception as exc:
        genx_failed = True
        generation_warnings.append("AI generation failed; fallback content was used.")
        result = {}
    if not result.get("caption"):
        genx_failed = True
        result = _template_from_intelligence(
            webapp_data,
            platform,
            objective=objective,
            tone=tone,
            include_hashtags=include_hashtags,
            include_cta=include_cta,
        )

    # Filter banned system hashtags from result
    hashtag_strategy = build_hashtag_strategy(webapp_data, platform)
    merged_hashtags = result.get("hashtags", []) or hashtag_strategy["hashtags"]
    if hashtag_strategy["hashtags"]:
        merged_hashtags = list(dict.fromkeys([*hashtag_strategy["hashtags"], *merged_hashtags]))
    result["hashtags"] = _filter_hashtags(merged_hashtags, business_name=webapp.name or "")

    media_urls = await get_media_url(platform, webapp_data, qwen_key or hf_token)
    content_type = "video" if platform in VIDEO_PLATFORMS else "image"
    genx_configured = bool(genx_key)
    provider_attempted = "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template"))
    provider_name = result.get("provider") or ("template" if genx_failed else provider_attempted)
    generation_status = (
        "genx_success"
        if provider_name == "genx"
        else ("genx_failed_fallback_used" if genx_configured and provider_name != "template" else ("template_fallback" if provider_name == "template" else "fallback_provider_success"))
    )
    generation_message = "Generation completed"
    if generation_status != "genx_success":
        generation_message = "Generated in degraded mode; review before posting."
    platform_review = {
        "platform_fit_score": 78 if generation_status != "genx_success" else 86,
        "algorithm_fit_suggestions": ["Prefer platform-native formatting and hooks."],
        "terms_policy_warnings": [],
        "customer_conversion_suggestions": ["Use clear CTA and audience-specific value proposition."],
        "follower_growth_suggestions": ["Iterate hooks and posting cadence from performance data."],
    }

    logger.info(
        "generate_content user=%s webapp=%s platform=%s provider=%s",
        current_user.id, webapp_id, platform, provider_name,
    )
    grounding_review = score_business_grounding(result.get("caption", ""), webapp_data)
    quality_gate = evaluate_quality_gate(
        business_grounding_score=int(grounding_review["business_grounding_score"]),
        hashtag_relevance_score=int(hashtag_strategy["hashtag_relevance_score"]),
    )
    recent_rows = (
        db.query(ContentModel)
        .filter(
            ContentModel.user_id == current_user.id,
            ContentModel.webapp_id == webapp_id,
            ContentModel.platform == platform,
        )
        .order_by(ContentModel.created_at.desc())
        .limit(6)
        .all()
    )
    similarities = [_similarity(str(result.get("caption", "")), str(row.caption or "")) for row in recent_rows]
    max_similarity = max(similarities) if similarities else 0.0
    uniqueness_score = int(max(0, min(100, round((1 - max_similarity) * 100))))
    variation_seed = str(uuid.uuid4())
    duplicate_warning = "Possible duplicate copy detected; review before publishing." if max_similarity >= 0.9 else ""

    db_content = ContentModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        webapp_id=webapp_id,
        platform=platform,
        type=content_type,
        status=ContentStatus.PENDING,
        title=result.get("title", "Generated Content"),
        caption=result.get("caption", ""),
        hashtags=result.get("hashtags", []),
        media_urls=media_urls,
        generation_metadata={
            **_generation_package(platform, result, provider_name, "configured" if genx_configured else "not_configured", generation_message, genx_configured),
            **_truthful_generation_metadata(
                provider_attempted=provider_attempted,
                provider_actual=provider_name,
                model_attempted=(settings.GENX_DEFAULT_MODEL if provider_attempted == "genx" else (settings.QWEN_MODEL if provider_attempted == "qwen" else "template")),
                model_actual=result.get("model", ""),
                task_used="text-generation",
                capability_used="platform_copy",
                generation_status=generation_status,
                degraded=generation_status != "genx_success",
                reason=("GenX model invalid/not found; fallback provider used." if genx_configured and provider_name != "genx" else ""),
                missing_capabilities=[],
                asset_generation_status="generated" if media_urls else "prompt_or_script_only",
                scrape_provider=intelligence.get("source_provider", "manual"),
                scrape_status=intelligence.get("scrape_status", "failed"),
                platform_review=platform_review,
            ),
            "source_route": "/content/generate",
            "source_action": "single_generate",
            "source_business_snapshot": source_business_snapshot,
            "business_name": webapp.name or "",
            "provider_actual": provider_name,
            "provider_attempted": provider_attempted,
            "generation_status": generation_status,
            "scrape_provider": intelligence.get("source_provider", "manual"),
            "scrape_status": intelligence.get("scrape_status", "failed"),
            "warnings": generation_warnings,
            "preview_title": result.get("title", "Generated Content"),
            "preview_summary": str(result.get("caption", ""))[:220],
            "hooks": [str(result.get("caption", "")).split("\n", 1)[0][:120]] if result.get("caption") else [],
            "fallback_chain": [provider_attempted, provider_name, "template"],
            "variation_seed": variation_seed,
            "uniqueness_score": uniqueness_score,
            "degraded": generation_status != "genx_success",
            "model": result.get("model", ""),
            "business_grounding_score": grounding_review["business_grounding_score"],
            "hashtag_relevance_score": hashtag_strategy["hashtag_relevance_score"],
            "creative_relevance_score": grounding_review["business_grounding_score"],
            "quality_gate": quality_gate["status"],
            "quality_gate_issues": quality_gate["issues"],
            "needs_review_duplicate": max_similarity >= 0.9,
            "parent_content_id": None,
        },
    )
    if duplicate_warning:
        db_content.generation_metadata["warnings"] = [*generation_warnings, duplicate_warning]
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return db_content


@router.post("/generate-all")
async def generate_all_content(
    payload: GenerateAllRequest = Body(default_factory=GenerateAllRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    """Batch generate AI content for launch platforms for one business profile."""
    from app.models.webapp import WebApp
    webapp = None
    if payload.webapp_id:
        webapp = db.query(WebApp).filter(WebApp.id == payload.webapp_id, WebApp.user_id == current_user.id).first()
    if not webapp:
        webapp = db.query(WebApp).filter(WebApp.user_id == current_user.id, WebApp.is_active == True).order_by(WebApp.created_at.desc()).first()
    if not webapp:
        raise HTTPException(status_code=400, detail="No active web apps found.")

    requested = payload.platforms or launch_platforms()
    platforms = filter_launch_platforms(requested) or launch_platforms()

    items: list[dict] = []
    warnings: list[str] = []
    for platform in platforms:
        try:
            item = await generate_content(
                webapp_id=webapp.id,
                platform=platform,
                db=db,
                current_user=current_user,
            )
            items.append({
                "id": item.id,
                "platform": item.platform,
                "title": item.title,
                "caption": item.caption,
                "generation_metadata": item.generation_metadata,
            })
        except Exception as exc:
            items.append({
                "platform": platform,
                "error": "generation_failed",
            })
            warnings.append(f"{platform}: generation failed")

    return {
        "count": len(items),
        "items": items,
        "generator_summary": {
            "platforms_requested": platforms,
            "success_count": len([i for i in items if "error" not in i]),
            "error_count": len([i for i in items if "error" in i]),
        },
        "warnings": warnings,
    }


@router.post("/generate-creative")
async def generate_creative(
    payload: GenerateCreativeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    from app.models.webapp import WebApp
    from app.services.platform_format_strategy import select_formats
    from app.services.media_generation import (
        generate_image_asset,
        generate_image_prompt,
        generate_video_script,
        generate_short_video_brief,
        generate_youtube_kit,
        generate_tiktok_reels_kit,
        generate_voiceover_script,
        generate_talking_avatar_script,
        generate_talking_avatar_video,
        generate_thumbnail_prompt,
        generate_carousel_outline,
    )
    from app.services.platform_intelligence import review_content
    from app.services.business_grounding import build_business_grounding_context, score_business_grounding
    from app.services.content_quality_gate import evaluate_quality_gate
    from app.services.creative_brief_builder import score_creative_relevance

    webapp = db.query(WebApp).filter(WebApp.id == payload.webapp_id, WebApp.user_id == current_user.id).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    hf_token = _get_hf_token(db, current_user)
    qwen_key = _get_qwen_key(db, current_user)
    openai_key = _get_openai_key(db, current_user)
    genx_key = _get_genx_key(db, current_user)
    strategy = select_formats(payload.platform, requested_format=payload.format, auto_select=payload.auto_select_format)
    selected_format = strategy["formats"][0]
    effective_product_focus = payload.product_focus or payload.offer or None
    webapp_data = {
        "name": webapp.name or "",
        "description": webapp.description or "",
        "category": getattr(webapp, "category", "") or "",
        "target_audience": payload.audience or getattr(webapp, "target_audience", "") or "",
        "objective": payload.objective or "",
        "tone": payload.tone or "",
        "key_features": webapp.key_features or [],
        "products_services": webapp.key_features or [],
        "market_location": getattr(webapp, "market_location", "") or "",
        "brand_voice": getattr(webapp, "brand_voice", "") or "",
    }
    if effective_product_focus:
        webapp_data["products_services"] = [effective_product_focus, *list(webapp_data.get("products_services") or [])][:5]
    source_business_snapshot = {
        "id": webapp.id,
        "name": webapp.name or "",
        "url": str(getattr(webapp, "url", "") or ""),
        "description": webapp.description or "",
        "category": getattr(webapp, "category", "") or "",
        "target_audience": webapp_data["target_audience"],
        "products_services": webapp_data["products_services"],
        "market_location": webapp_data.get("market_location", ""),
        "brand_voice": webapp_data.get("brand_voice", ""),
    }
    grounding_context = build_business_grounding_context(webapp_data)
    webapp_data["description"] = f"{grounding_context['prompt_prefix']} {webapp_data['description']}".strip()

    result: dict[str, object] = {
        "platform": normalize_catalog_platform(payload.platform),
        "format": selected_format,
        "image_url": None,
        "video_url": None,
        "avatar_url": None,
    }
    provider_actual = "template"
    model_or_task = selected_format
    persisted_content_id: str | None = None
    if selected_format in {"image_prompt", "generated_image"}:
        image_prompt = await generate_image_prompt(webapp_data, payload.platform, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result["image_prompt"] = image_prompt["image_prompt"]
        provider_actual = image_prompt["provider"]
        if selected_format == "generated_image":
            image_asset = await generate_image_asset(image_prompt=result["image_prompt"], hf_token=hf_token)
            result["image_url"] = image_asset["image_url"]
            result["asset_generation_status"] = image_asset["asset_generation_status"]
    elif selected_format in {"short_video_brief", "video_script"}:
        if selected_format == "short_video_brief":
            brief = await generate_short_video_brief(webapp_data, payload.platform, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
            result["video_script"] = brief["video_script"]
            result["shot_list"] = brief["shot_list"]
            provider_actual = brief["provider"]
        else:
            script = await generate_video_script(webapp_data, payload.platform, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
            result["video_script"] = script["video_script"]
            provider_actual = script["provider"]
        result["asset_generation_status"] = "prompt_or_script_only"
    elif selected_format == "youtube_video_kit":
        kit = await generate_youtube_kit(webapp_data, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result.update(kit)
        provider_actual = kit["provider"]
        result["asset_generation_status"] = "prompt_or_script_only"
    elif selected_format == "tiktok_reels_kit":
        kit = await generate_tiktok_reels_kit(webapp_data, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result.update(kit)
        provider_actual = kit["provider"]
        result["asset_generation_status"] = "prompt_or_script_only"
    elif selected_format == "voiceover_script":
        voice = await generate_voiceover_script(webapp_data, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result.update(voice)
        provider_actual = voice["provider"]
        result["asset_generation_status"] = "prompt_or_script_only"
    elif selected_format in {"talking_avatar_script", "talking_avatar_video"}:
        avatar_script = await generate_talking_avatar_script(webapp_data, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result.update(avatar_script)
        provider_actual = avatar_script["provider"]
        if selected_format == "talking_avatar_video":
            avatar_video = await generate_talking_avatar_video(avatar_script=result["avatar_script"], hf_token=hf_token)
            result["avatar_url"] = avatar_video["avatar_url"]
            result["asset_generation_status"] = avatar_video["asset_generation_status"]
        else:
            result["asset_generation_status"] = "prompt_or_script_only"
    elif selected_format == "thumbnail_prompt":
        thumbnail = await generate_thumbnail_prompt(webapp_data, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result.update(thumbnail)
        provider_actual = thumbnail["provider"]
        result["asset_generation_status"] = "prompt_or_script_only"
    elif selected_format == "carousel":
        carousel = await generate_carousel_outline(webapp_data, qwen_key=qwen_key, hf_token=hf_token, openai_key=openai_key, genx_key=genx_key)
        result.update(carousel)
        provider_actual = carousel["provider"]
        result["asset_generation_status"] = "prompt_or_script_only"
    else:
        generated = await generate_content(
            webapp_id=payload.webapp_id,
            platform=payload.platform,
            objective=payload.objective,
            tone=payload.tone,
            audience=payload.audience,
            db=db,
            current_user=current_user,
        )
        metadata = generated.generation_metadata or {}
        result.update({"text": generated.caption, "hashtags": generated.hashtags, "asset_generation_status": metadata.get("asset_generation_status", "prompt_or_script_only")})
        provider_actual = str(metadata.get("provider_actual", "template"))
        model_or_task = str(metadata.get("model_actual", metadata.get("model", "text-generation")))
        persisted_content_id = generated.id

    content_for_review = result.get("text") or result.get("video_script") or result.get("avatar_script") or result.get("image_prompt") or ""
    platform_review = review_content(platform=payload.platform, content=str(content_for_review))
    grounding_review = score_business_grounding(str(content_for_review), webapp_data)
    creative_review = score_creative_relevance(
        str(content_for_review),
        str(result.get("image_prompt") or result.get("thumbnail_prompt") or ""),
        webapp_data,
    )
    quality_gate = evaluate_quality_gate(
        business_grounding_score=int(grounding_review["business_grounding_score"]),
        hashtag_relevance_score=80,
        creative_relevance_score=int(creative_review["creative_relevance_score"]),
    )
    recent_rows = (
        db.query(ContentModel)
        .filter(
            ContentModel.user_id == current_user.id,
            ContentModel.webapp_id == payload.webapp_id,
            ContentModel.platform == normalize_catalog_platform(payload.platform),
        )
        .order_by(ContentModel.created_at.desc())
        .limit(6)
        .all()
    )
    content_text_value = str(content_for_review)
    similarities = [_similarity(content_text_value, str(row.caption or "")) for row in recent_rows]
    max_similarity = max(similarities) if similarities else 0.0
    uniqueness_score = int(max(0, min(100, round((1 - max_similarity) * 100))))
    variation_seed = str(uuid.uuid4())
    generation_status = "genx_failed_qwen_fallback" if genx_key and provider_actual == "qwen" else ("success" if provider_actual != "template" else "template_fallback")
    degraded = generation_status != "success"
    generation_metadata = {
        "format": selected_format,
        "source_route": "/content/generate-creative",
        "source_action": "creative_generate",
        "source_business_snapshot": source_business_snapshot,
        "business_name": webapp.name or "",
        "provider_attempted": "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template")),
        "provider_actual": provider_actual,
        "model_actual": model_or_task,
        "task_used": selected_format,
        "capability_used": selected_format,
        "generation_status": generation_status,
        "degraded": degraded,
        "reason": "" if not degraded else "Provider fallback or template output used.",
        "asset_generation_status": result.get("asset_generation_status", "prompt_or_script_only"),
        "image_prompt": result.get("image_prompt"),
        "video_script": result.get("video_script"),
        "shot_list": result.get("shot_list"),
        "voiceover_script": result.get("voiceover_script"),
        "avatar_script": result.get("avatar_script"),
        "thumbnail_prompt": result.get("thumbnail_prompt"),
        "carousel_slides": result.get("carousel_slides"),
        "platform_fit_score": platform_review["platform_fit_score"],
        "terms_policy_warnings": platform_review["terms_policy_warnings"],
        "media_job_ids": result.get("media_job_ids", []),
        "media_asset_ids": result.get("media_asset_ids", []),
        "warnings": platform_review["risks"],
        "preview_title": str(result.get("title") or f"{webapp.name or 'Business'} • {payload.platform.title()}"),
        "preview_summary": content_text_value[:220],
        "hooks": [content_text_value.split("\n", 1)[0][:120]] if content_text_value else [],
        "variation_seed": variation_seed,
        "uniqueness_score": uniqueness_score,
        "fallback_chain": ["genx", "qwen", "huggingface", "template"],
        "cta": result.get("cta"),
        "business_grounding_score": grounding_review["business_grounding_score"],
        "creative_relevance_score": creative_review["creative_relevance_score"],
        "quality_gate": quality_gate["status"],
        "quality_gate_issues": quality_gate["issues"],
        "needs_review_duplicate": max_similarity >= 0.9,
        "parent_content_id": None,
    }
    media_urls = [str(url) for url in [result.get("image_url"), result.get("video_url"), result.get("avatar_url")] if isinstance(url, str) and url]
    hashtags = _filter_hashtags(_safe_list(result.get("hashtags")), business_name=webapp.name or "")
    if persisted_content_id is None:
        db_content = ContentModel(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            webapp_id=payload.webapp_id,
            platform=normalize_catalog_platform(payload.platform),
            type=_content_type_for_format(selected_format),
            status=ContentStatus.PENDING,
            title=str(result.get("title") or f"{webapp.name or 'Business'} • {payload.platform.title()}"),
            caption=str(content_for_review),
            hashtags=hashtags,
            media_urls=media_urls,
            generation_metadata=generation_metadata,
        )
        db.add(db_content)
        db.commit()
        db.refresh(db_content)
        persisted_content_id = db_content.id
    else:
        existing = db.query(ContentModel).filter(
            ContentModel.id == persisted_content_id,
            ContentModel.user_id == current_user.id,
        ).first()
        if existing:
            existing_metadata = dict(existing.generation_metadata or {})
            existing_metadata.update(generation_metadata)
            existing.generation_metadata = existing_metadata
            db.commit()
            db.refresh(existing)
    return {
        **result,
        "platform_fit_score": platform_review["platform_fit_score"],
        "algorithm_suggestions": platform_review["algorithm_fit_suggestions"],
        "terms_policy_warnings": platform_review["terms_policy_warnings"],
        "customer_conversion_suggestions": platform_review["customer_conversion_suggestions"],
        "follower_growth_suggestions": platform_review["follower_growth_suggestions"],
        "provider_attempted": "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template")),
        "provider_actual": provider_actual,
        "model_or_task": model_or_task,
        "status": generation_status,
        "warnings": platform_review["risks"],
        "missing_capabilities": [],
        "degraded": degraded,
        "content_id": persisted_content_id,
    }


@router.post("/generate-pack")
async def generate_pack(
    payload: GeneratePackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    items = []
    for platform in filter_launch_platforms(payload.platforms):
        formats = payload.formats if not payload.auto_select_formats else []
        if not formats:
            from app.services.platform_format_strategy import select_formats
            formats = select_formats(platform, auto_select=True)["formats"][:3]
        for fmt in formats:
            item = await generate_creative(
                payload=GenerateCreativeRequest(
                    webapp_id=payload.webapp_id,
                    platform=platform,
                    format=fmt,
                    objective=payload.objective,
                    tone=payload.tone,
                    audience=payload.audience,
                    offer=payload.offer,
                    product_focus=payload.product_focus,
                    auto_select_format=payload.auto_select_formats,
                ),
                db=db,
                current_user=current_user,
            )
            items.append(item)
    return {"count": len(items), "items": items}


@router.post("/{content_id}/approve", response_model=Content)
async def approve_content(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(ContentModel).filter(ContentModel.id == content_id, ContentModel.user_id == current_user.id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    content.status = ContentStatus.APPROVED
    db.commit()
    db.refresh(content)
    return content


@router.post("/{content_id}/reject", response_model=Content)
async def reject_content(
    content_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject content and immediately queue regeneration for the same webapp/platform."""
    content = db.query(ContentModel).filter(
        ContentModel.id == content_id, ContentModel.user_id == current_user.id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    content.status = ContentStatus.REJECTED
    db.commit()
    db.refresh(content)

    # Immediately regenerate a replacement in the background
    rejected_webapp_id = content.webapp_id
    rejected_platform = content.platform
    user_id = current_user.id

    async def _regenerate_content_after_rejection():
        import logging
        logger = logging.getLogger(__name__)
        from app.db.base import SessionLocal
        from app.models.webapp import WebApp
        from app.services.media_service import get_media_url, VIDEO_PLATFORMS
        async_db = SessionLocal()
        try:
            user = async_db.query(User).filter(User.id == user_id).first()
            if not user:
                return
            webapp = async_db.query(WebApp).filter(
                WebApp.id == rejected_webapp_id, WebApp.user_id == user_id
            ).first()
            if not webapp:
                return
            hf_token = _get_hf_token(async_db, user)
            qwen_key = _get_qwen_key(async_db, user)
            openai_key = _get_openai_key(async_db, user)
            genx_key = _get_genx_key(async_db, user)
            webapp_data = {
                "name": webapp.name,
                "url": str(webapp.url),
                "description": webapp.description,
                "category": webapp.category,
                "target_audience": getattr(webapp, "target_audience", ""),
                "key_features": webapp.key_features or [],
            }
            result = await _generate_text_content(
                webapp_data, rejected_platform, hf_token, openai_key, qwen_key, genx_key
            )
            media_urls = await get_media_url(rejected_platform, webapp_data, qwen_key or hf_token)
            content_type = "video" if rejected_platform in VIDEO_PLATFORMS else "image"
            generator_name = "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template"))
            new_content = ContentModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                webapp_id=rejected_webapp_id,
                platform=rejected_platform,
                type=content_type,
                status=ContentStatus.PENDING,
                title=result.get("title", "Generated Content"),
                caption=result.get("caption", ""),
                hashtags=result.get("hashtags", []),
                media_urls=media_urls,
                parent_content_id=content_id,
                generation_metadata={
                    **_generation_package(
                        rejected_platform,
                        result,
                        generator_name,
                        "configured" if genx_key else "not_configured",
                        "Regenerated after rejection.",
                        bool(genx_key),
                    ),
                    "source": "reject_regen",
                    "replaced_content_id": content_id,
                },
            )
            async_db.add(new_content)
            async_db.commit()
            logger.info(
                "Replacement content %s generated for rejected content %s on %s",
                new_content.id, content_id, rejected_platform,
            )
        except Exception as exc:
            logger.error(
                "Failed to regenerate content after rejection of %s: %s",
                content_id, exc, exc_info=True,
            )
        finally:
            async_db.close()

    background_tasks.add_task(_regenerate_content_after_rejection)
    return content


@router.post("/approve-all")
async def approve_all_content(
    content_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(ContentModel).filter(
        ContentModel.id.in_(content_ids), ContentModel.user_id == current_user.id
    ).update({"status": ContentStatus.APPROVED}, synchronize_session=False)
    db.commit()
    return {"message": f"Approved {len(content_ids)} items"}


@router.put("/{content_id}", response_model=Content)
async def update_content(
    content_id: str,
    content_update: ContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(ContentModel).filter(ContentModel.id == content_id, ContentModel.user_id == current_user.id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    update_data = content_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(content, field, value)
    db.commit()
    db.refresh(content)
    return content
