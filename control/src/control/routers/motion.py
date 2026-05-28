"""XYZ motion control."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from control.deps import AppContext, call_adapter, get_ctx

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/motion", tags=["motion"])


class MoveAbsRequest(BaseModel):
    x: float
    y: float
    z: float


class MoveRelRequest(BaseModel):
    axis: str
    distance: float


class SetTopRightRequest(BaseModel):
    x: float
    y: float


def _broadcast_position(ctx: AppContext) -> None:
    lx, ly, lz = ctx.state.position_logical
    mx, my, mz = ctx.state.position_machine
    ctx.broadcast("position", {
        "x": lx, "y": ly, "z": lz,
        "machine_x": mx, "machine_y": my, "machine_z": mz,
    })


async def _refresh_position(ctx: AppContext) -> None:
    """Read actual position from the adapter and update both machine and logical state.

    The logical position is derived from the machine reading via a pure
    transform (origin offset + axis inversion/swap), so the WS ``position``
    topic always reports the user's coordinate system — never the gantry's.
    """
    worker = ctx.workers.get("chipshover")
    machine = await call_adapter(worker, ctx.shover.get_position)
    ctx.state.position_machine = machine
    ctx.state.position_logical = ctx.shover.machine_to_logical(*machine)


@router.post("/move_abs")
async def move_abs(req: MoveAbsRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.move_absolute_logical, req.x, req.y, req.z)
    await _refresh_position(ctx)
    _broadcast_position(ctx)
    lx, ly, lz = ctx.state.position_logical
    return {"ok": True, "position": [lx, ly, lz]}


@router.post("/move_rel")
async def move_rel(req: MoveRelRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    if req.axis.upper() not in ("X", "Y", "Z"):
        raise HTTPException(status_code=400, detail=f"Invalid axis: {req.axis}")
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.move_relative, req.axis.upper(), req.distance)
    await _refresh_position(ctx)
    _broadcast_position(ctx)
    lx, ly, lz = ctx.state.position_logical
    return {"ok": True, "position": [lx, ly, lz]}


@router.post("/home")
async def home(ctx: AppContext = Depends(get_ctx)) -> dict:
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.home)
    await _refresh_position(ctx)
    _broadcast_position(ctx)
    lx, ly, lz = ctx.state.position_logical
    return {"ok": True, "position": [lx, ly, lz]}


@router.post("/set_origin")
async def set_origin(ctx: AppContext = Depends(get_ctx)) -> dict:
    """Mark current position as logical (0, 0, 0)."""
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.set_origin)
    ctx.state.origin_set = True
    await _refresh_position(ctx)
    _broadcast_position(ctx)
    ctx.broadcast_state()
    return {"ok": True, "origin_set": True}


@router.post("/set_top_right")
async def set_top_right(req: SetTopRightRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.state.top_right = (req.x, req.y)
    ctx.state.top_right_set = True
    ctx.broadcast_state()
    return {"ok": True, "top_right": [req.x, req.y]}
