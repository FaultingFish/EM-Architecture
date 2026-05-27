"""GlitchTarget endpoints."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from emfi_protocol.projects import GlitchTarget

log = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/targets", tags=["targets"])


@router.get("", response_model=List[GlitchTarget])
async def list_targets(project_id: str) -> List[GlitchTarget]:
    log.debug("GET targets project=%s", project_id)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("", response_model=GlitchTarget)
async def add_target(project_id: str, target: GlitchTarget) -> GlitchTarget:
    """Append to targets.json and git commit."""
    log.info("POST target project=%s pc=0x%x", project_id, target.pc_address)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.delete("/{pc_address}")
async def remove(project_id: str, pc_address: int) -> dict:
    log.warning("DELETE target project=%s pc=0x%x", project_id, pc_address)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
