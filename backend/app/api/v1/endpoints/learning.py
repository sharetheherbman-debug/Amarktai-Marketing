from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.analytics import Analytics
from app.models.content import Content
from app.models.user import User
from app.services.learning_loop import learning_insights, learning_status, run_learning_now

router = APIRouter()


class RunLearningRequest(BaseModel):
    webapp_id: str | None = None


@router.post("/run-now")
async def run_learning(
    payload: RunLearningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    metrics_records = db.query(Analytics).filter(Analytics.user_id == current_user.id).count()
    generated_count = db.query(Content).filter(Content.user_id == current_user.id).count()
    return run_learning_now(
        user_id=current_user.id,
        webapp_id=payload.webapp_id,
        metrics_records=metrics_records,
        generated_count=generated_count,
    )


@router.get("/status")
async def get_learning_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return learning_status(current_user.id)


@router.get("/insights")
async def get_learning_insights(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return learning_insights(current_user.id)


@router.get("/insights/{webapp_id}")
async def get_learning_insights_for_business(
    webapp_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload = learning_insights(current_user.id, webapp_id=webapp_id)
    if not payload.get("insights"):
        raise HTTPException(status_code=404, detail="No learning insights for this business.")
    return payload
