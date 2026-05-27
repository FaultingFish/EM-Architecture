"""Artifact download — Control pulls the .elf from these endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(prefix="/projects/{project_id}/builds/{sha}", tags=["artifacts"])


@router.get("/firmware.elf")
async def firmware_elf(project_id: str, sha: str) -> FileResponse:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/firmware.bin")
async def firmware_bin(project_id: str, sha: str) -> FileResponse:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/firmware.lst")
async def firmware_lst(project_id: str, sha: str) -> FileResponse:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
