"""Project CRUD endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from emfi_protocol.projects import Project

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    template: str  # e.g. "c_ti_hal" | "rust_b01lers"
    language: str
    hal: str
    description: Optional[str] = None


@router.get("", response_model=List[Project])
async def list_all() -> List[Project]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("", response_model=Project)
async def create(req: CreateProjectRequest) -> Project:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{project_id}", response_model=Project)
async def get_one(project_id: str) -> Project:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.delete("/{project_id}")
async def delete(project_id: str) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{project_id}/tree")
async def tree(project_id: str) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{project_id}/file")
async def get_file(project_id: str, path: str) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.put("/{project_id}/file")
async def put_file(project_id: str, path: str, contents: str) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
