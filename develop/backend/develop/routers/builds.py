"""Build endpoints."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from emfi_protocol.projects import BuildArtifact

log = logging.getLogger(__name__)

router = APIRouter(tags=["builds"])


class BuildRequest(BaseModel):
    version: Optional[str] = None  # git tag; defaults to current HEAD


@router.post("/projects/{project_id}/build", response_model=BuildArtifact)
async def trigger(project_id: str, req: BuildRequest = BuildRequest()) -> BuildArtifact:
    """Kick a build. Streams logs via WS topic `build_log`."""
    log.info("POST /projects/%s/build version=%s", project_id, req.version)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/projects/{project_id}/builds", response_model=List[BuildArtifact])
async def list_builds(project_id: str) -> List[BuildArtifact]:
    log.debug("GET /projects/%s/builds", project_id)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/projects/{project_id}/builds/{sha}", response_model=BuildArtifact)
async def get_build(project_id: str, sha: str) -> BuildArtifact:
    log.debug("GET /projects/%s/builds/%s", project_id, sha)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
