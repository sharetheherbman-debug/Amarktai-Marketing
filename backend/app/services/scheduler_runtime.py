from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus
from app.models.marketing_runtime import SchedulerItem, SchedulerMode, SchedulerStatus
from app.services.platform_catalog import platform_label
from app.services.posting_readiness import platform_posting_state


def parse_iso_datetime(value: str | None, fallback: datetime | None = None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if fallback is not None:
        return fallback
    return datetime.now(timezone.utc)


def scheduler_item_payload(item: SchedulerItem) -> dict[str, Any]:
    metadata = dict(item.metadata_json or {})
    return {
        "id": item.id,
        "business_id": item.business_id,
        "content_id": item.content_id,
        "platform": item.platform,
        "platform_label": platform_label(item.platform),
        "title": item.title,
        "planned_at": item.planned_at.isoformat() if item.planned_at else None,
        "status": item.status,
        "posting_readiness": item.posting_readiness,
        "mode": item.mode,
        "notes": item.notes,
        "metadata": metadata,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def upsert_scheduler_item(
    db: Session,
    *,
    user_id: str,
    content: Content,
    planned_at: datetime,
    mode: str = SchedulerMode.MANUAL.value,
    notes: str | None = None,
) -> SchedulerItem:
    item = db.query(SchedulerItem).filter(
        SchedulerItem.user_id == user_id,
        SchedulerItem.content_id == content.id,
    ).first()
    posting_state = platform_posting_state(db, user_id, content.platform)
    if not item:
        item = SchedulerItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            business_id=content.webapp_id,
            content_id=content.id,
            platform=content.platform,
        )
        db.add(item)

    item.title = content.title or content.caption[:120] or f"{platform_label(content.platform)} content"
    item.planned_at = planned_at
    item.status = SchedulerStatus.SCHEDULED.value
    item.posting_readiness = "can_post_now" if posting_state.get("can_post_now") else "planning_only"
    item.mode = mode
    item.notes = notes
    item.metadata_json = {
        **dict(item.metadata_json or {}),
        "posting_supported": bool(posting_state.get("posting_supported")),
        "oauth_configured": bool(posting_state.get("oauth_configured")),
        "user_connected": bool(posting_state.get("user_connected")),
        "missing_requirements": list(posting_state.get("missing", [])),
        "user_message": posting_state.get("user_message"),
    }
    content.scheduled_for = planned_at
    content.status = ContentStatus.SCHEDULED
    return item
