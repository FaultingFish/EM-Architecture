"""Disassembly endpoint — returns AssemblyListing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from emfi_protocol.projects import AssemblyListing

router = APIRouter(
    prefix="/projects/{project_id}/builds/{sha}", tags=["disassembly"]
)


@router.get("/disassembly", response_model=AssemblyListing)
async def disassembly(project_id: str, sha: str) -> AssemblyListing:
    """Parsed `arm-none-eabi-objdump -d` output. View renders this in Monaco."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
