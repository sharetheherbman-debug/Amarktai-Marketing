from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.content import Content, ContentStatus
from app.models.user import User

router = APIRouter()


class ScheduleRequest(BaseModel):
    content_id: str
    scheduled_for: datetime | None = None


@router.post("/schedule")
async def schedule_content(
    payload: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = db.query(Content).filter(
        Content.id == payload.content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    scheduled_for = payload.scheduled_for
    if scheduled_for is None:
        scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=15)
    content.scheduled_for = scheduled_for
    content.status = ContentStatus.SCHEDULED
    db.commit()
    db.refresh(content)
    return {
        "ok": True,
        "content_id": content.id,
        "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        "scheduled_for": content.scheduled_for.isoformat() if content.scheduled_for else None,
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
        db.query(Content)
        .filter(
            Content.user_id == current_user.id,
            Content.status == ContentStatus.SCHEDULED,
            Content.scheduled_for != None,  # noqa: E711
            Content.scheduled_for >= now,
        )
        .order_by(Content.scheduled_for.asc())
        .limit(limit)
        .all()
    )
    return {
        "count": len(rows),
        "items": [
            {
                "id": c.id,
                "platform": c.platform,
                "title": c.title,
                "scheduled_for": c.scheduled_for.isoformat() if c.scheduled_for else None,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            }
            for c in rows
        ],
    }
