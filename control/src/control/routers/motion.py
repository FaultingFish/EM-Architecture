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


@router.post("/move_abs")
async def move_abs(req: MoveAbsRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.move_absolute_logical, req.x, req.y, req.z)
    ctx.state.position_logical = (req.x, req.y, req.z)
    _broadcast_position(ctx)
    return {"ok": True, "position": [req.x, req.y, req.z]}


@router.post("/move_rel")
async def move_rel(req: MoveRelRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    if req.axis.upper() not in ("X", "Y", "Z"):
        raise HTTPException(status_code=400, detail=f"Invalid axis: {req.axis}")
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.move_relative, req.axis.upper(), req.distance)
    lx, ly, lz = ctx.state.position_logical
    idx = {"X": 0, "Y": 1, "Z": 2}[req.axis.upper()]
    pos = list(ctx.state.position_logical)
    pos[idx] += req.distance
    ctx.state.position_logical = tuple(pos)  # type: ignore[assignment]
    _broadcast_position(ctx)
    return {"ok": True, "position": pos}


@router.post("/home")
async def home(ctx: AppContext = Depends(get_ctx)) -> dict:
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.home)
    ctx.state.position_logical = (0.0, 0.0, 0.0)
    ctx.state.position_machine = (0.0, 0.0, 0.0)
    _broadcast_position(ctx)
    return {"ok": True, "position": [0.0, 0.0, 0.0]}


@router.post("/set_origin")
async def set_origin(ctx: AppContext = Depends(get_ctx)) -> dict:
    """Mark current position as logical (0, 0, 0)."""
    worker = ctx.workers.get("chipshover")
    await call_adapter(worker, ctx.shover.set_origin)
    ctx.state.origin_set = True
    ctx.state.position_logical = (0.0, 0.0, 0.0)
    _broadcast_position(ctx)
    ctx.broadcast_state()
    return {"ok": True, "origin_set": True}


@router.post("/set_top_right")
async def set_top_right(req: SetTopRightRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.state.top_right = (req.x, req.y)
    ctx.state.top_right_set = True
    ctx.broadcast_state()
    return {"ok": True, "top_right": [req.x, req.y]}
