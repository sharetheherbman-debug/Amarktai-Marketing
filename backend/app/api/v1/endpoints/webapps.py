from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session
import uuid

from app.db.base import get_db
from app.models.webapp import WebApp as WebAppModel, MAX_BUSINESSES_PER_USER
from app.models.user import User
from app.schemas.webapp import WebApp, WebAppCreate, WebAppUpdate
from app.api.deps import get_current_user, is_admin_user

router = APIRouter()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def _run_scrape(webapp_id: str) -> None:
    """Background task: scrape the webapp URL and store the results.

    Uses Firecrawl as the primary scraping provider when FIRECRAWL_API_KEY is
    configured; falls back to httpx + BeautifulSoup automatically.
    """
    import logging
    from app.db.base import SessionLocal
    from app.services.scraper import scrape_page
    from app.core.config import settings

    _logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        webapp = db.query(WebAppModel).filter(WebAppModel.id == webapp_id).first()
        if not webapp:
            return
        firecrawl_key = settings.FIRECRAWL_API_KEY or None
        scraped = await scrape_page(
            str(webapp.url),
            timeout=30,
            firecrawl_api_key=firecrawl_key,
        )
        webapp.scraped_data = {
            "scraped_at": datetime.utcnow().isoformat(),
            "title": scraped.title,
            "meta_description": scraped.meta_description,
            "headings": scraped.headings[:10],
            "paragraphs": scraped.paragraphs[:5],
            "social_links": scraped.social_links[:20],
            "full_text": scraped.full_text[:2000],
            "error": scraped.error,
            "status": "error" if scraped.error else "ok",
            "provider": scraped.provider,
        }
        db.commit()
    except Exception as exc:
        _logger.warning(
            "Background scrape failed for webapp %s: %s", webapp_id, exc
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[WebApp])
async def get_webapps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all web apps for the current user."""
    webapps = db.query(WebAppModel).filter(WebAppModel.user_id == current_user.id).all()
    return webapps

@router.get("/{webapp_id}", response_model=WebApp)
async def get_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific web app by ID."""
    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")
    return webapp

@router.post("/", response_model=WebApp, status_code=status.HTTP_201_CREATED)
async def create_webapp(
    webapp: WebAppCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new web app / business (max 20 per user; unlimited for admin).

    Immediately queues a background scrape of the webapp URL so the AI has
    rich context before the first content generation run.
    """
    # Admin users bypass all limits
    if not is_admin_user(current_user):
        existing_count = db.query(WebAppModel).filter(
            WebAppModel.user_id == current_user.id,
        ).count()
        if existing_count >= MAX_BUSINESSES_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum of {MAX_BUSINESSES_PER_USER} businesses per user reached.",
            )
    db_webapp = WebAppModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        **webapp.model_dump()
    )
    db.add(db_webapp)
    db.commit()
    db.refresh(db_webapp)

    # Auto-scrape in the background so creation is instant for the user
    background_tasks.add_task(_run_scrape, db_webapp.id)

    return db_webapp

@router.post("/{webapp_id}/scrape")
async def scrape_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Scrape the webapp URL synchronously and store results.

    Uses Firecrawl as primary provider when FIRECRAWL_API_KEY is configured;
    falls back to httpx + BeautifulSoup.  Returns the scraped_data dict so
    the frontend can display insights immediately.
    """
    from app.services.scraper import scrape_page
    from app.core.config import settings

    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    firecrawl_key = settings.FIRECRAWL_API_KEY or None
    scraped = await scrape_page(
        str(webapp.url),
        timeout=30,
        firecrawl_api_key=firecrawl_key,
    )
    scraped_data: dict[str, Any] = {
        "scraped_at": datetime.utcnow().isoformat(),
        "title": scraped.title,
        "meta_description": scraped.meta_description,
        "headings": scraped.headings[:10],
        "paragraphs": scraped.paragraphs[:5],
        "social_links": scraped.social_links[:20],
        "full_text": scraped.full_text[:2000],
        "error": scraped.error,
        "status": "error" if scraped.error else "ok",
        "provider": scraped.provider,
    }
    webapp.scraped_data = scraped_data
    db.commit()

    return {
        "message": "Scraped successfully" if not scraped.error else f"Scrape error: {scraped.error}",
        "scraped_data": scraped_data,
    }


@router.put("/{webapp_id}", response_model=WebApp)
async def update_webapp(
    webapp_id: str,
    webapp_update: WebAppUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a web app."""
    db_webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not db_webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    update_data = webapp_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_webapp, field, value)

    db.commit()
    db.refresh(db_webapp)
    return db_webapp

@router.delete("/{webapp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a web app."""
    db_webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not db_webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    db.delete(db_webapp)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Media upload
# ---------------------------------------------------------------------------

_ALLOWED_MEDIA_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    "video/mp4", "video/webm", "video/quicktime",
    "application/pdf",
}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/{webapp_id}/media")
async def upload_media(
    webapp_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload a brand media asset and attach it to the business/app.

    Accepts images, videos, and PDFs up to 50 MB.
    Files are stored under MEDIA_UPLOAD_DIR (default: /tmp/amarktai_media).
    Returns the stored asset metadata including a relative URL.
    """
    import os
    from app.core.config import settings

    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Allowed: images, videos, PDF.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit.")

    # Determine storage directory
    upload_dir = settings.MEDIA_UPLOAD_DIR or "/tmp/amarktai_media"
    webapp_dir = os.path.join(upload_dir, current_user.id, webapp_id)
    os.makedirs(webapp_dir, exist_ok=True)

    # Build a unique filename preserving the extension
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    asset_id = str(uuid.uuid4())
    filename = f"{asset_id}{ext}"
    file_path = os.path.join(webapp_dir, filename)

    with open(file_path, "wb") as fh:
        fh.write(data)

    # Build relative URL served via static mount (or direct path for now)
    relative_url = f"/media/{current_user.id}/{webapp_id}/{filename}"

    # Append to media_assets JSON list
    asset_meta: dict[str, Any] = {
        "id": asset_id,
        "name": file.filename or filename,
        "url": relative_url,
        "type": content_type,
        "size": len(data),
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    current_assets: list = list(webapp.media_assets or [])
    current_assets.append(asset_meta)
    webapp.media_assets = current_assets
    db.commit()

    return {"message": "Upload successful", "asset": asset_meta}


@router.delete("/{webapp_id}/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    webapp_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove a previously uploaded media asset from the business/app."""
    import os
    from app.core.config import settings

    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    current_assets: list = list(webapp.media_assets or [])
    asset = next((a for a in current_assets if a.get("id") == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Try to delete the physical file (best-effort)
    try:
        upload_dir = settings.MEDIA_UPLOAD_DIR or "/tmp/amarktai_media"
        ext = os.path.splitext(asset.get("name", ""))[1] or ".bin"
        filename = f"{asset_id}{ext}"
        file_path = os.path.join(upload_dir, current_user.id, webapp_id, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    webapp.media_assets = [a for a in current_assets if a.get("id") != asset_id]
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
