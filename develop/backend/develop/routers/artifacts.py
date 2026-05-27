"""Artifact download — Control pulls the .elf from these endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/builds/{sha}", tags=["artifacts"])


@router.get("/firmware.elf")
async def firmware_elf(project_id: str, sha: str) -> FileResponse:
    log.info("Download firmware.elf project=%s sha=%s", project_id, sha)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/firmware.bin")
async def firmware_bin(project_id: str, sha: str) -> FileResponse:
    log.info("Download firmware.bin project=%s sha=%s", project_id, sha)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/firmware.lst")
async def firmware_lst(project_id: str, sha: str) -> FileResponse:
    log.info("Download firmware.lst project=%s sha=%s", project_id, sha)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
