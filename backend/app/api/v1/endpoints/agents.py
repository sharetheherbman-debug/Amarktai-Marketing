from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.agents.agent_specs import all_agents

router = APIRouter()


@router.get("/status")
async def agents_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    agents = [agent.as_dict() for agent in all_agents()]
    return {
        "agents": agents,
        "autonomous_posting_note": "Auto-posting is only enabled when OAuth scopes, targets, and worker runtime are verified.",
    }
