"""XYZ motion control."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/motion", tags=["motion"])


class MoveAbsRequest(BaseModel):
    x: float
    y: float
    z: float


class MoveRelRequest(BaseModel):
    axis: str  # "X" | "Y" | "Z"
    distance: float


class SetTopRightRequest(BaseModel):
    x: float
    y: float


@router.post("/move_abs")
async def move_abs(req: MoveAbsRequest) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/move_rel")
async def move_rel(req: MoveRelRequest) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/home")
async def home() -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/set_origin")
async def set_origin() -> dict:
    """Mark current position as logical (0, 0, 0)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/set_top_right")
async def set_top_right(req: SetTopRightRequest) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
