"""Target MCU flashing + debugging via XDS110."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/target", tags=["target"])


class FlashRequest(BaseModel):
    build_sha: str
    elf_url: str  # http URL or file:// path on the lab box


class DebugAttachRequest(BaseModel):
    build_sha: str
    elf_url: Optional[str] = None
    gdb_port: int = 3333
    telnet_port: int = 4444


@router.post("/flash")
async def flash(req: FlashRequest) -> dict:
    """Flash the MSPM0L2228 via TI dslite/UniFlash CLI subprocess.

    Resolves elf_url (download if http, copy if file://), then invokes the
    programmer binary configured in config.programmer.dslite_bin.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/reset")
async def reset() -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/debug_attach")
async def debug_attach(req: DebugAttachRequest) -> dict:
    """Start OpenOCD attached to the target for debugger sessions.

    Spawns `openocd -f <board-config>` in the background. Returns gdb/telnet
    port info. Used for combined SW + HW attack analysis (e.g. step through
    code while glitching it).
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/debug_detach")
async def debug_detach() -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
