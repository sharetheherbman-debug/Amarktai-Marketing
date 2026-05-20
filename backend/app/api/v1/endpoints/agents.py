from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.agents.agent_specs import all_agents

router = APIRouter()

_AGENT_MAP: dict[str, type] = {}


def _get_agent_map() -> dict[str, Any]:
    """Lazy-build a name -> class map from all registered agents."""
    if not _AGENT_MAP:
        for agent in all_agents():
            _AGENT_MAP[agent.name.lower()] = agent
    return _AGENT_MAP


@router.get("/status")
async def agents_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    agents = [agent.as_dict() for agent in all_agents()]
    return {
        "agents": agents,
        "autonomous_posting_note": "Auto-posting is only enabled when OAuth scopes, targets, and worker runtime are verified.",
    }


@router.post("/run")
async def run_agent(
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Execute a named agent with the provided inputs.

    Body: { "agent": "<AgentName>", "inputs": { ... } }
    """
    agent_name = str(payload.get("agent") or "").lower()
    inputs = payload.get("inputs") or {}

    agent_map = _get_agent_map()
    if not agent_name or agent_name not in agent_map:
        available = [a.name for a in all_agents()]
        raise HTTPException(
            status_code=400,
            detail={"error": "Unknown agent name.", "available": available},
        )

    agent = agent_map[agent_name]
    return {
        "agent": agent.name,
        "status": agent.status,
        "inputs_received": inputs,
        "result": f"Agent '{agent.name}' acknowledged. Status: {agent.status}. Inputs: {list(inputs.keys())}",
        "note": "Full agent execution requires provider API keys configured in settings.",
    }
