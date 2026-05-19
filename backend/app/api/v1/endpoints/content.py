"""
Content endpoints — generate, approve, reject, manage social media content.

AI generation uses a tiered provider stack (primary → fallback → template).
Template-based generation is always available as a guaranteed fallback.

Rejecting a post immediately triggers regeneration for the same webapp/platform.

Designed and created by AmarktAI Marketing
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, enforce_content_quota
from app.db.base import get_db
from app.models.content import Content as ContentModel, ContentStatus
from app.models.user import User
from app.schemas.content import Content, ContentUpdate
from app.services.social_rules import get_social_rule, resolve_platform_key
from app.services.provider_catalog import resolve_user_api_key

router = APIRouter()


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
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    """Generate AI content (text + image/video). Falls back to templates if no AI key configured."""
    from app.models.webapp import WebApp
    from app.services.media_service import get_media_url, VIDEO_PLATFORMS

    webapp = db.query(WebApp).filter(WebApp.id == webapp_id, WebApp.user_id == current_user.id).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    hf_token = _get_hf_token(db, current_user)
    openai_key = _get_openai_key(db, current_user)
    qwen_key = _get_qwen_key(db, current_user)
    genx_key = _get_genx_key(db, current_user)
    firecrawl_key = _get_firecrawl_key(db, current_user)

    webapp_data = {
        "name": webapp.name,
        "url": str(webapp.url),
        "description": webapp.description,
        "category": webapp.category,
        "target_audience": webapp.target_audience,
        "key_features": webapp.key_features or [],
    }

    result = await _generate_text_content(webapp_data, platform, hf_token, openai_key, qwen_key, genx_key)
    media_urls = await get_media_url(platform, webapp_data, qwen_key or hf_token)
    content_type = "video" if platform in VIDEO_PLATFORMS else "image"
    # Truthful generation status for go-live readiness
    genx_configured = bool(genx_key)
    ai_used = not result.get("_generation_error") and bool(genx_key or qwen_key or hf_token)
    generation_status = "configured" if genx_configured else "not_configured"
    generation_message = (
        "GENX configured: live AI generation enabled."
        if genx_configured
        else "GENX_API_KEY is not configured. Generated output uses degraded fallback guidance; configure GENX for production-quality AI generation."
    )
    provider_name = "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template"))

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
        generation_metadata=_generation_package(platform, result, provider_name, generation_status, generation_message, genx_configured),
    )
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return db_content


@router.post("/generate-all")
async def generate_all_content(
    db: Session = Depends(get_db),
    current_user: User = Depends(enforce_content_quota),
):
    """Batch generate AI content for all active platforms + webapps."""
    from app.models.user_api_key import UserIntegration
    from app.models.webapp import WebApp
    from app.services.hf_generator import HuggingFaceGenerator
    from app.services.media_service import get_media_url, VIDEO_PLATFORMS
    from app.services.scraper import scrape_page

    hf_token = _get_hf_token(db, current_user)
    openai_key = _get_openai_key(db, current_user)
    qwen_key = _get_qwen_key(db, current_user)
    genx_key = _get_genx_key(db, current_user)

    webapps = db.query(WebApp).filter(WebApp.user_id == current_user.id, WebApp.is_active == True).all()
    if not webapps:
        raise HTTPException(status_code=400, detail="No active web apps found.")

    connected = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id, UserIntegration.is_connected == True
    ).all()
    platforms = [i.platform for i in connected] or ["instagram", "twitter", "linkedin", "facebook"]

    created = []
    for webapp in webapps[:2]:
        live_description = webapp.description or ""
        try:
            scraped = await scrape_page(str(webapp.url), timeout=15, firecrawl_api_key=firecrawl_key)
            if scraped and not scraped.error and scraped.full_text:
                live_description = scraped.full_text[:1200]
        except Exception:
            pass

        webapp_data = {
            "name": webapp.name,
            "url": str(webapp.url),
            "description": live_description or webapp.description,
            "category": webapp.category,
            "target_audience": webapp.target_audience,
            "key_features": webapp.key_features or [],
        }

        active_token = genx_key or qwen_key or hf_token
        generation_status = "configured" if genx_key else "not_configured"
        if active_token:
            try:
                from app.services.ai_provider import AIProvider
                provider = AIProvider.from_keys(
                    genx_key=genx_key or "",
                    qwen_key=qwen_key or "",
                    hf_token=hf_token or "",
                    openai_key=openai_key or "",
                )
                results = await provider.generate_batch(webapp_data, platforms)
            except Exception:
                results = {p: HuggingFaceGenerator._fallback_content(webapp_data, p) for p in platforms}
        else:
            results = {p: HuggingFaceGenerator._fallback_content(webapp_data, p) for p in platforms}

        ai_used = bool(active_token)
        generator_name = "genx" if genx_key else ("qwen" if qwen_key else ("huggingface" if hf_token else "template"))
        for platform, content_dict in results.items():
            if content_dict.get("_generation_error") and not content_dict.get("caption"):
                continue
            media_urls = await get_media_url(platform, webapp_data, active_token)
            content_type = "video" if platform in VIDEO_PLATFORMS else "image"
            db_content = ContentModel(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                webapp_id=webapp.id,
                platform=platform,
                type=content_type,
                status=ContentStatus.PENDING,
                title=content_dict.get("title", "Generated Post"),
                caption=content_dict.get("caption", ""),
                hashtags=content_dict.get("hashtags", []),
                media_urls=media_urls,
                generation_metadata={
                    **_generation_package(
                        platform,
                        content_dict,
                        generator_name,
                        generation_status,
                        "GENX configured: live AI generation enabled." if genx_key else "GENX_API_KEY is missing; batch generation is running in degraded mode.",
                        bool(genx_key),
                    ),
                    "source": "manual_batch",
                },
            )
            db.add(db_content)
            created.append(db_content)

    db.commit()
    return {
        "message": f"Generated {len(created)} content items across {len(platforms)} platforms",
        "count": len(created),
        "platforms": platforms,
        "generator": generator_name,
        "generation_status": "configured" if genx_key else "not_configured",
        "degraded": not bool(genx_key),
        "degraded_reason": None if genx_key else "GENX_API_KEY missing; configure GenX for full production quality output.",
    }


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
