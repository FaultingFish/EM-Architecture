"""Git operation endpoints — commit, tag, log."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/git", tags=["git"])


class CommitRequest(BaseModel):
    message: str


class TagRequest(BaseModel):
    name: str


@router.post("/commit")
async def commit(project_id: str, req: CommitRequest) -> dict:
    """Stage all changes and create a git commit."""
    log.info("git commit project=%s msg=%s", project_id, req.message[:80])
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/tag")
async def tag(project_id: str, req: TagRequest) -> dict:
    """Create a git tag (lightweight)."""
    log.info("git tag project=%s name=%s", project_id, req.name)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/log")
async def log_entries(project_id: str, limit: int = 50) -> List[dict]:
    """Return recent git log entries."""
    log.debug("git log project=%s limit=%d", project_id, limit)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
