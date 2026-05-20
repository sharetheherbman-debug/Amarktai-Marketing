from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.content import Content
from app.models.marketing_runtime import SchedulerItem, SchedulerStatus
from app.models.user import User
from app.services.scheduler_runtime import parse_iso_datetime, scheduler_item_payload, upsert_scheduler_item

router = APIRouter()


class SchedulerItemCreate(BaseModel):
    content_id: str
    planned_at: datetime | None = None
    mode: str = "manual"
    notes: str | None = None


class SchedulerItemUpdate(BaseModel):
    planned_at: datetime | None = None
    status: str | None = None
    mode: str | None = None
    notes: str | None = None


def _get_item_or_404(db: Session, item_id: str, user_id: str) -> SchedulerItem:
    item = db.query(SchedulerItem).filter(
        SchedulerItem.id == item_id,
        SchedulerItem.user_id == user_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Scheduler item not found")
    return item


def _get_content_or_404(db: Session, content_id: str, user_id: str) -> Content:
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == user_id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.get("/items")
async def list_scheduler_items(
    start: str | None = None,
    end: str | None = None,
    business_id: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    query = db.query(SchedulerItem).filter(SchedulerItem.user_id == current_user.id)
    if business_id:
        query = query.filter(SchedulerItem.business_id == business_id)
    if platform:
        query = query.filter(SchedulerItem.platform == platform)
    if status:
        query = query.filter(SchedulerItem.status == status)
    if start:
        query = query.filter(SchedulerItem.planned_at >= parse_iso_datetime(start))
    if end:
        query = query.filter(SchedulerItem.planned_at <= parse_iso_datetime(end))
    rows = query.order_by(SchedulerItem.planned_at.asc()).all()
    return {"count": len(rows), "items": [scheduler_item_payload(row) for row in rows]}


@router.post("/items")
async def create_scheduler_item(
    payload: SchedulerItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = _get_content_or_404(db, payload.content_id, current_user.id)
    planned_at = payload.planned_at or (datetime.now(timezone.utc) + timedelta(hours=1))
    item = upsert_scheduler_item(
        db,
        user_id=current_user.id,
        content=content,
        planned_at=planned_at,
        mode=payload.mode,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(item)
    return scheduler_item_payload(item)


@router.get("/items/{item_id}")
async def get_scheduler_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return scheduler_item_payload(_get_item_or_404(db, item_id, current_user.id))


@router.put("/items/{item_id}")
async def update_scheduler_item(
    item_id: str,
    payload: SchedulerItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    item = _get_item_or_404(db, item_id, current_user.id)
    if payload.planned_at:
        item.planned_at = payload.planned_at
    if payload.status:
        item.status = payload.status
    if payload.mode:
        item.mode = payload.mode
    if payload.notes is not None:
        item.notes = payload.notes
    content = _get_content_or_404(db, item.content_id, current_user.id)
    content.scheduled_for = item.planned_at
    db.commit()
    db.refresh(item)
    return scheduler_item_payload(item)


@router.delete("/items/{item_id}")
async def delete_scheduler_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    item = _get_item_or_404(db, item_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"deleted": True, "id": item_id}


@router.post("/items/{item_id}/mark-posted")
async def mark_scheduler_item_posted(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    item = _get_item_or_404(db, item_id, current_user.id)
    item.status = SchedulerStatus.POSTED.value
    content = _get_content_or_404(db, item.content_id, current_user.id)
    content.posted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return scheduler_item_payload(item)


@router.post("/items/{item_id}/mark-failed")
async def mark_scheduler_item_failed(
    item_id: str,
    reason: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    item = _get_item_or_404(db, item_id, current_user.id)
    item.status = SchedulerStatus.FAILED.value
    item.metadata_json = {**dict(item.metadata_json or {}), "failure_reason": reason or ""}
    db.commit()
    db.refresh(item)
    return scheduler_item_payload(item)


@router.post("/items/{item_id}/reschedule")
async def reschedule_item(
    item_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    item = _get_item_or_404(db, item_id, current_user.id)
    new_planned_at_raw = payload.get("planned_at")
    if not new_planned_at_raw:
        raise HTTPException(status_code=400, detail="planned_at is required for reschedule")
    if isinstance(new_planned_at_raw, str):
        new_planned_at = parse_iso_datetime(new_planned_at_raw)
    else:
        new_planned_at = new_planned_at_raw
    reason = payload.get("reason") or ""
    item.planned_at = new_planned_at
    item.status = SchedulerStatus.SCHEDULED.value
    item.metadata_json = {**dict(item.metadata_json or {}), "reschedule_reason": reason}
    content = _get_content_or_404(db, item.content_id, current_user.id)
    content.scheduled_for = new_planned_at
    db.commit()
    db.refresh(item)
    return scheduler_item_payload(item)


async def scheduler_calendar(
    start: str,
    end: str,
    business_id: str | None = None,
    platform: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    query = db.query(SchedulerItem).filter(
        SchedulerItem.user_id == current_user.id,
        SchedulerItem.planned_at >= parse_iso_datetime(start),
        SchedulerItem.planned_at <= parse_iso_datetime(end),
    )
    if business_id:
        query = query.filter(SchedulerItem.business_id == business_id)
    if platform:
        query = query.filter(SchedulerItem.platform == platform)
    rows = query.order_by(SchedulerItem.planned_at.asc()).all()
    return {"count": len(rows), "items": [scheduler_item_payload(row) for row in rows]}


@router.post("/schedule")
async def schedule_content_compat(
    payload: SchedulerItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = _get_content_or_404(db, payload.content_id, current_user.id)
    planned_at = payload.planned_at or (datetime.now(timezone.utc) + timedelta(minutes=15))
    item = upsert_scheduler_item(
        db,
        user_id=current_user.id,
        content=content,
        planned_at=planned_at,
        mode=payload.mode,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(item)
    return {
        "ok": True,
        "content_id": content.id,
        "scheduler_item_id": item.id,
        "status": item.status,
        "scheduled_for": item.planned_at.isoformat() if item.planned_at else None,
    }


@router.get("/upcoming")
async def upcoming_scheduled(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    now = datetime.now(timezone.utc)
    rows = (
        db.query(SchedulerItem)
        .filter(
            SchedulerItem.user_id == current_user.id,
            SchedulerItem.status == SchedulerStatus.SCHEDULED.value,
            SchedulerItem.planned_at >= now,
        )
        .order_by(SchedulerItem.planned_at.asc())
        .limit(limit)
        .all()
    )
    return {"count": len(rows), "items": [scheduler_item_payload(row) for row in rows]}
