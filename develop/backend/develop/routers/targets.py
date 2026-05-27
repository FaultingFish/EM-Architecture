"""GlitchTarget endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from emfi_protocol.projects import GlitchTarget

router = APIRouter(prefix="/projects/{project_id}/targets", tags=["targets"])


@router.get("", response_model=List[GlitchTarget])
async def list_targets(project_id: str) -> List[GlitchTarget]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("", response_model=GlitchTarget)
async def add_target(project_id: str, target: GlitchTarget) -> GlitchTarget:
    """Append to targets.json and git commit."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.delete("/{pc_address}")
async def remove(project_id: str, pc_address: int) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
