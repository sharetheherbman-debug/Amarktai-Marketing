from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.marketing_runtime import MediaAsset, MediaJob, MediaJobStatus
from app.models.user import User

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
