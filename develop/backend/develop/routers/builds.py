"""Build endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from emfi_protocol.projects import BuildArtifact

router = APIRouter(tags=["builds"])


class BuildRequest(BaseModel):
    version: Optional[str] = None  # git tag; defaults to current HEAD


@router.post("/projects/{project_id}/build", response_model=BuildArtifact)
async def trigger(project_id: str, req: BuildRequest = BuildRequest()) -> BuildArtifact:
    """Kick a build. Streams logs via WS topic `build_log`."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/projects/{project_id}/builds", response_model=List[BuildArtifact])
async def list_builds(project_id: str) -> List[BuildArtifact]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/projects/{project_id}/builds/{sha}", response_model=BuildArtifact)
async def get_build(project_id: str, sha: str) -> BuildArtifact:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
