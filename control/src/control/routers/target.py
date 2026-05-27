"""Target MCU flashing + debugging via XDS110.

Flash sequence: power on DUT via Scaffold board, then flash via XDS110.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from control.deps import AppContext, call_adapter, call_subprocess_adapter, get_ctx

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/target", tags=["target"])


class FlashRequest(BaseModel):
    build_sha: str
    elf_url: str


class DebugAttachRequest(BaseModel):
    build_sha: str
    elf_url: Optional[str] = None
    gdb_port: int = 3333
    telnet_port: int = 4444


@router.post("/flash")
async def flash(req: FlashRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    """Flash the MSPM0L2228 via XDS110.

    Sequence:
    1. Power-cycle the DUT via Scaffold to ensure it's in a known state
    2. Flash the ELF via dslite/UniFlash subprocess
    """
    LOGGER.info("Flash requested: build_sha=%s elf_url=%s", req.build_sha, req.elf_url)

    scaffold_worker = ctx.workers.get("scaffold")
    await call_adapter(scaffold_worker, ctx.scaffold.dut_power_cycle)
    LOGGER.info("DUT power-cycled via Scaffold, proceeding to flash")

    elf_path = await _resolve_elf(req.elf_url)

    result = await call_subprocess_adapter(ctx.xds110.flash, elf_path)

    ctx.broadcast("device_status", {"name": "xds110", "connected": True})
    LOGGER.info("Flash complete: build_sha=%s result=%s", req.build_sha, result)
    return {"ok": True, "build_sha": req.build_sha, "flash_result": result}


@router.post("/reset")
async def reset(ctx: AppContext = Depends(get_ctx)) -> dict:
    await call_subprocess_adapter(ctx.xds110.reset)
    return {"ok": True}


@router.post("/debug_attach")
async def debug_attach(req: DebugAttachRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    """Start OpenOCD attached to the target for debugger sessions."""
    result = await call_subprocess_adapter(
        ctx.xds110.attach_debugger,
        gdb_port=req.gdb_port,
        telnet_port=req.telnet_port,
    )
    LOGGER.info("OpenOCD attached: gdb=%d telnet=%d", req.gdb_port, req.telnet_port)
    return {"ok": True, "gdb_port": req.gdb_port, "telnet_port": req.telnet_port, **(result or {})}


@router.post("/debug_detach")
async def debug_detach(ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.xds110.detach_debugger()
    return {"ok": True}


async def _resolve_elf(elf_url: str) -> Path:
    """Resolve an ELF URL to a local file path.

    Supports ``file:///path`` (local) and ``http(s)://`` (download from Develop).
    """
    if elf_url.startswith("file://"):
        return Path(elf_url[7:])

    if elf_url.startswith(("http://", "https://")):
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(elf_url)
            resp.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(suffix=".elf", delete=False)
        tmp.write(resp.content)
        tmp.close()
        LOGGER.info("Downloaded ELF to %s (%d bytes)", tmp.name, len(resp.content))
        return Path(tmp.name)

    return Path(elf_url)
