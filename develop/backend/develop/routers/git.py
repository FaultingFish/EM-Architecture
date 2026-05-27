"""Git operation endpoints — commit, tag, log."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


router = APIRouter(prefix="/projects/{project_id}/git", tags=["git"])


class CommitRequest(BaseModel):
    message: str


class TagRequest(BaseModel):
    name: str


@router.post("/commit")
async def commit(project_id: str, req: CommitRequest) -> dict:
    """Stage all changes and create a git commit."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/tag")
async def tag(project_id: str, req: TagRequest) -> dict:
    """Create a git tag (lightweight)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/log")
async def log(project_id: str, limit: int = 50) -> List[dict]:
    """Return recent git log entries."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
