"""Claude Code CLI agent endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


class AgentRequest(BaseModel):
    prompt: str
    model: str = "opus"  # Reserved for future model selection


@router.post("")
async def run_agent(project_id: str, req: AgentRequest) -> dict:
    """Spawn `claude` in the project directory.

    Returns immediately with a job ID; stream output via WS topic `agent_output`.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
