from __future__ import annotations

import shutil
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.content import Content as ContentModel
from app.models.marketing_runtime import MediaAsset, MediaJob, MediaJobStatus
from app.models.user import User
from app.services.asset_query_builder import build_asset_query
from app.services.pixabay_asset_router import (
    normalize_pixabay_image,
    normalize_pixabay_video,
    not_supported_payload,
)
from app.services.pixabay_client import PixabayClient
from app.services.provider_catalog import resolve_user_api_key

router = APIRouter()


def _job_payload(job: MediaJob) -> dict[str, object]:
    return {
        "id": job.id,
        "business_id": job.business_id,
        "content_id": job.content_id,
        "provider": job.provider,
        "model": job.model,
        "task": job.task,
        "external_job_id": job.external_job_id,
        "status": job.status,
        "prompt": job.prompt,
        "result_url": job.result_url,
        "error_message": job.error_message,
        "metadata": job.metadata_json or {},
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _asset_payload(asset: MediaAsset) -> dict[str, object]:
    return {
        "id": asset.id,
        "business_id": asset.business_id,
        "content_id": asset.content_id,
        "media_job_id": asset.media_job_id,
        "provider": asset.provider,
        "model": asset.model,
        "asset_type": asset.asset_type,
        "title": asset.title,
        "url": asset.url,
        "preview_url": asset.preview_url,
        "prompt": asset.prompt,
        "metadata": asset.metadata_json or {},
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


@router.get("/jobs")
async def list_media_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rows = (
        db.query(MediaJob)
        .filter(MediaJob.user_id == current_user.id)
        .order_by(MediaJob.created_at.desc())
        .all()
    )
    return {"count": len(rows), "items": [_job_payload(row) for row in rows]}


@router.get("/jobs/{job_id}")
async def get_media_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    row = db.query(MediaJob).filter(MediaJob.id == job_id, MediaJob.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Media job not found")
    return _job_payload(row)


@router.post("/jobs/{job_id}/refresh")
async def refresh_media_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    row = db.query(MediaJob).filter(MediaJob.id == job_id, MediaJob.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Media job not found")
    if row.status in {MediaJobStatus.QUEUED.value, MediaJobStatus.RUNNING.value} and row.result_url:
        row.status = MediaJobStatus.COMPLETED.value
        db.commit()
        db.refresh(row)
    return _job_payload(row)


@router.post("/jobs/{job_id}/cancel")
async def cancel_media_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    row = db.query(MediaJob).filter(MediaJob.id == job_id, MediaJob.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Media job not found")
    row.status = MediaJobStatus.CANCELLED.value
    db.commit()
    db.refresh(row)
    return _job_payload(row)


@router.get("/assets")
async def list_media_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rows = (
        db.query(MediaAsset)
        .filter(MediaAsset.user_id == current_user.id)
        .order_by(MediaAsset.created_at.desc())
        .all()
    )
    return {"count": len(rows), "items": [_asset_payload(row) for row in rows]}


@router.get("/assets/{asset_id}")
async def get_media_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    row = db.query(MediaAsset).filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Media asset not found")
    return _asset_payload(row)


def _pixabay_client(db: Session, user: User) -> PixabayClient:
    key = resolve_user_api_key(db, user.id, "PIXABAY_API_KEY", settings.PIXABAY_API_KEY)
    return PixabayClient(api_key=key)


def _business_query_context(db: Session, user_id: str, business_id: str | None) -> dict[str, Any]:
    if not business_id:
        return {}
    from app.models.webapp import WebApp
    row = db.query(WebApp).filter(WebApp.id == business_id, WebApp.user_id == user_id).first()
    if not row:
        return {}
    return {
        "business_name": row.name or "",
        "category": getattr(row, "category", "") or "",
        "products_services": row.key_features or [],
        "audience": getattr(row, "target_audience", "") or "",
    }


@router.get("/tooling/status")
async def tooling_status() -> dict[str, Any]:
    return {
        "ffmpeg_installed": bool(shutil.which("ffmpeg")),
        "remotion_configured": False,
        "whisper_cpp_configured": False,
        "coqui_configured": bool(settings.COQUI_API_KEY),
        "qdrant_configured": False,
        "mem0_configured": False,
    }


@router.get("/pixabay/search")
async def pixabay_search(
    q: str | None = None,
    category: str = "business",
    platform: str = "instagram",
    business_id: str | None = None,
    page: int = 1,
    per_page: int = 20,
    media_type: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    client = _pixabay_client(db, current_user)
    ctx = _business_query_context(db, current_user.id, business_id)
    query = (q or "").strip() or build_asset_query(
        business_name=str(ctx.get("business_name", "")),
        category=str(ctx.get("category", "") or category),
        products_services=ctx.get("products_services") if isinstance(ctx.get("products_services"), list) else [],
        audience=str(ctx.get("audience", "")),
        platform=platform,
    )
    image_resp = {"items": []}
    video_resp = {"items": []}
    if media_type in {"all", "image"}:
        image_resp = await client.search_images(q=query, category=category, page=page, per_page=per_page, safesearch="true")
    if media_type in {"all", "video"}:
        video_resp = await client.search_videos(q=query, category=category, page=page, per_page=per_page, safesearch="true")
    items = [
        *[normalize_pixabay_image(item, query=query, category=category, platform=platform) for item in image_resp.get("items", [])],
        *[normalize_pixabay_video(item, query=query, category=category, platform=platform) for item in video_resp.get("items", [])],
    ]
    suggestions = []
    if items and all(bool(item.get("needs_review")) for item in items[:5]):
        suggestions.append("Use a more specific business query for higher relevance.")
    return {"status": "ok", "query": query, "count": len(items), "items": items, "suggestions": suggestions}


@router.get("/pixabay/photos")
async def pixabay_photos(
    q: str | None = None,
    category: str = "business",
    platform: str = "instagram",
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    client = _pixabay_client(db, current_user)
    query = (q or "business marketing").strip()
    data = await client.search_images(q=query, category=category, image_type="photo", page=page, per_page=per_page, safesearch="true")
    items = [normalize_pixabay_image(item, query=query, category=category, platform=platform) for item in data.get("items", [])]
    return {"status": data.get("status", "ok"), "query": query, "count": len(items), "items": items}


@router.get("/pixabay/illustrations")
async def pixabay_illustrations(
    q: str | None = None,
    category: str = "business",
    platform: str = "instagram",
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    client = _pixabay_client(db, current_user)
    query = (q or "business marketing").strip()
    data = await client.search_images(q=query, category=category, image_type="illustration", page=page, per_page=per_page, safesearch="true")
    items = [normalize_pixabay_image(item, query=query, category=category, platform=platform) for item in data.get("items", [])]
    return {"status": data.get("status", "ok"), "query": query, "count": len(items), "items": items}


@router.get("/pixabay/vectors")
async def pixabay_vectors(
    q: str | None = None,
    category: str = "business",
    platform: str = "instagram",
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    client = _pixabay_client(db, current_user)
    query = (q or "business marketing").strip()
    data = await client.search_images(q=query, category=category, image_type="vector", page=page, per_page=per_page, safesearch="true")
    items = [normalize_pixabay_image(item, query=query, category=category, platform=platform) for item in data.get("items", [])]
    return {"status": data.get("status", "ok"), "query": query, "count": len(items), "items": items}


@router.get("/pixabay/videos")
async def pixabay_videos(
    q: str | None = None,
    category: str = "business",
    platform: str = "instagram",
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    client = _pixabay_client(db, current_user)
    query = (q or "business marketing").strip()
    data = await client.search_videos(q=query, category=category, page=page, per_page=per_page, safesearch="true")
    items = [normalize_pixabay_video(item, query=query, category=category, platform=platform) for item in data.get("items", [])]
    return {"status": data.get("status", "ok"), "query": query, "count": len(items), "items": items}


@router.get("/pixabay/music")
async def pixabay_music() -> dict[str, Any]:
    return not_supported_payload()


@router.get("/pixabay/sound-effects")
async def pixabay_sound_effects() -> dict[str, Any]:
    return not_supported_payload()


@router.get("/pixabay/gifs")
async def pixabay_gifs() -> dict[str, Any]:
    return not_supported_payload()


@router.get("/pixabay/3d-models")
async def pixabay_3d_models() -> dict[str, Any]:
    return not_supported_payload()


@router.get("/pixabay/users")
async def pixabay_users() -> dict[str, Any]:
    return not_supported_payload()


@router.post("/assets")
async def create_media_asset(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    asset = MediaAsset(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        business_id=str(payload.get("business_id") or ""),
        content_id=payload.get("content_id"),
        provider=str(payload.get("provider") or "pixabay"),
        model=str(payload.get("model") or ""),
        asset_type=str(payload.get("asset_type") or "image"),
        title=str(payload.get("title") or ""),
        url=payload.get("url"),
        preview_url=payload.get("preview_url"),
        prompt=payload.get("prompt"),
        metadata_json=payload.get("raw_metadata") if isinstance(payload.get("raw_metadata"), dict) else (payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _asset_payload(asset)


@router.delete("/assets/{asset_id}")
async def delete_media_asset(
    asset_id: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to delete this media asset.")
    deleted = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Media asset not found")
    return {"deleted": True, "id": asset_id}


@router.post("/content/items/{content_id}/attach-asset")
async def attach_asset_to_content(
    content_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = db.query(ContentModel).filter(ContentModel.id == content_id, ContentModel.user_id == current_user.id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    asset_id = str(payload.get("asset_id") or "")
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    asset.content_id = content.id
    metadata = dict(content.generation_metadata or {})
    ids = list(metadata.get("media_asset_ids") or [])
    if asset.id not in ids:
        ids.append(asset.id)
    metadata["media_asset_ids"] = ids
    metadata["attached_asset_provider"] = asset.provider
    content.generation_metadata = metadata
    db.commit()
    db.refresh(content)
    return {"attached": True, "content_id": content_id, "asset_id": asset.id}


@router.delete("/content/items/{content_id}/assets/{asset_id}")
async def detach_asset_from_content(
    content_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = db.query(ContentModel).filter(ContentModel.id == content_id, ContentModel.user_id == current_user.id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    if asset.content_id == content.id:
        asset.content_id = None
    metadata = dict(content.generation_metadata or {})
    ids = [value for value in list(metadata.get("media_asset_ids") or []) if str(value) != asset_id]
    metadata["media_asset_ids"] = ids
    content.generation_metadata = metadata
    db.commit()
    return {"detached": True, "content_id": content_id, "asset_id": asset_id}
