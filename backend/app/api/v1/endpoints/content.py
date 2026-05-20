"""
Content endpoints — generate, approve, reject, manage social media content.

AI generation uses a tiered provider stack (primary → fallback → template).
Template-based generation is always available as a guaranteed fallback.

Rejecting a post immediately triggers regeneration for the same webapp/platform.

Designed and created by AmarktAI Marketing
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from pydantic import BaseModel

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
from app.services.platform_catalog import filter_launch_platforms, launch_platforms, normalize_platform as normalize_catalog_platform

router = APIRouter()


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
    auto_select_format: bool = True


class GeneratePackRequest(BaseModel):
    webapp_id: str
    platforms: list[str] = ["instagram", "facebook", "linkedin", "twitter", "tiktok", "youtube", "reddit", "pinterest"]
    objective: str | None = None
    tone: str | None = None
    audience: str | None = None
    formats: list[str] = ["text_post", "image_prompt", "video_script", "thumbnail_prompt", "talking_avatar_script", "voiceover_script"]
    auto_select_formats: bool = True


class ScheduleContentRequest(BaseModel):
    scheduled_for: str | None = None


class ImproveContentRequest(BaseModel):
    objective: str | None = None
    tone: str | None = None
    audience: str | None = None


def _extract_intelligence(webapp) -> dict:
    if isinstance(webapp.scraped_data, dict):
        return webapp.scraped_data
    return {}


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
        hashtags = [f"#{tag}" for tag in (webapp_data.get("keywords") or [])[:6]]
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


def _content_item_payload(content: ContentModel) -> dict:
    metadata = content.generation_metadata or {}
    return {
        "id": content.id,
        "user_id": content.user_id,
        "webapp_id": content.webapp_id,
        "campaign_id": metadata.get("campaign_id"),
        "platform": content.platform,
        "format": metadata.get("format", content.type.value if hasattr(content.type, "value") else str(content.type)),
        "title": content.title,
        "caption": content.caption,
        "body": content.caption,
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
        "task_used": metadata.get("task_used"),
        "capability_used": metadata.get("capability_used"),
        "generation_status": metadata.get("generation_status", content.status.value if hasattr(content.status, "value") else str(content.status)),
        "degraded": bool(metadata.get("degraded")),
        "reason": metadata.get("reason"),
        "asset_generation_status": metadata.get("asset_generation_status"),
        "media_job_ids": _safe_list(metadata.get("media_job_ids")),
        "media_asset_ids": _safe_list(metadata.get("media_asset_ids")),
        "media_urls": _safe_list(content.media_urls),
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


@router.get("/", response_model=List[Content])
async def get_content(
    content_status: ContentStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    query = db.query(ContentModel).filter(ContentModel.user_id == current_user.id)
    if webapp_id:
        query = query.filter(ContentModel.webapp_id == webapp_id)
    if platform:
        query = query.filter(ContentModel.platform == normalize_catalog_platform(platform))
    rows = query.order_by(ContentModel.created_at.desc()).all()
    payload = [_content_item_payload(item) for item in rows]
    if fmt:
        payload = [item for item in payload if str(item.get("format", "")).lower() == fmt.lower()]
    if status:
        payload = [item for item in payload if str(item.get("generation_status", "")).lower() == status.lower()]
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
    return [_content_item_payload(item) for item in rows]


@router.delete("/items/{content_id}")
async def delete_content_item(
    content_id: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    return {"deleted": True, "id": content_id}


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
    content.status = ContentStatus.SCHEDULED
    content.scheduled_for = scheduled_for or (datetime.now(timezone.utc) + timedelta(hours=1))
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
        generation_metadata={**(content.generation_metadata or {}), "duplicated_from": content.id},
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
        db=db,
        current_user=current_user,
    )
    metadata = dict(improved.generation_metadata or {})
    metadata["improved_from"] = content.id
    improved.generation_metadata = metadata
    db.commit()
    db.refresh(improved)
    return _content_item_payload(improved)


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
    audience: str | None = None,
    include_hashtags: bool = True,
    include_cta: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    """Generate AI content (text + image/video). Falls back to templates if no AI key configured."""
    from app.models.webapp import WebApp
    from app.services.media_service import get_media_url, VIDEO_PLATFORMS

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
    }
    if product_focus:
        webapp_data["products_services"] = [product_focus, *list(webapp_data.get("products_services") or [])][:5]
    if campaign_type:
        webapp_data["campaign_type"] = campaign_type
    if objective:
        webapp_data["objective"] = objective
    if tone:
        webapp_data["tone"] = tone

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
            "provider_actual": provider_name,
            "provider_attempted": provider_attempted,
            "generation_status": generation_status,
            "scrape_provider": intelligence.get("source_provider", "manual"),
            "scrape_status": intelligence.get("scrape_status", "failed"),
            "warnings": generation_warnings,
            "degraded": generation_status != "genx_success",
            "model": result.get("model", ""),
        },
    )
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

    webapp = db.query(WebApp).filter(WebApp.id == payload.webapp_id, WebApp.user_id == current_user.id).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    hf_token = _get_hf_token(db, current_user)
    qwen_key = _get_qwen_key(db, current_user)
    openai_key = _get_openai_key(db, current_user)
    genx_key = _get_genx_key(db, current_user)
    strategy = select_formats(payload.platform, requested_format=payload.format, auto_select=payload.auto_select_format)
    selected_format = strategy["formats"][0]
    webapp_data = {
        "name": webapp.name,
        "description": webapp.description,
        "target_audience": payload.audience or webapp.target_audience,
        "objective": payload.objective,
        "tone": payload.tone,
    }

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
    generation_status = "genx_failed_qwen_fallback" if genx_key and provider_actual == "qwen" else ("success" if provider_actual != "template" else "template_fallback")
    degraded = generation_status != "success"
    generation_metadata = {
        "format": selected_format,
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
        "cta": result.get("cta"),
    }
    media_urls = [str(url) for url in [result.get("image_url"), result.get("video_url"), result.get("avatar_url")] if isinstance(url, str) and url]
    hashtags = _safe_list(result.get("hashtags"))
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
