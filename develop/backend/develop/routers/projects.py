"""Project CRUD endpoints."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from emfi_protocol.projects import Project

log = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    template: str  # e.g. "c_ti_hal" | "rust_b01lers"
    language: str
    hal: str
    description: Optional[str] = None


@router.get("", response_model=List[Project])
async def list_all() -> List[Project]:
    log.debug("GET /projects")
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("", response_model=Project)
async def create(req: CreateProjectRequest) -> Project:
    log.info("POST /projects name=%s template=%s", req.name, req.template)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{project_id}", response_model=Project)
async def get_one(project_id: str) -> Project:
    log.debug("GET /projects/%s", project_id)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.delete("/{project_id}")
async def delete(project_id: str) -> dict:
    log.warning("DELETE /projects/%s", project_id)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{project_id}/tree")
async def tree(project_id: str) -> dict:
    log.debug("GET /projects/%s/tree", project_id)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{project_id}/file")
async def get_file(project_id: str, path: str) -> dict:
    log.debug("GET /projects/%s/file path=%s", project_id, path)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.put("/{project_id}/file")
async def put_file(project_id: str, path: str, contents: str) -> dict:
    log.info("PUT /projects/%s/file path=%s", project_id, path)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
