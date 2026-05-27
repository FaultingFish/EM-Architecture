"""ChipSHOUTER control endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/shouter", tags=["shouter"])


class PulseRequest(BaseModel):
    voltage: Optional[int] = None
    pulse_width_ns: Optional[int] = None
    repeat: int = 1


class ConfigRequest(BaseModel):
    voltage: int
    pulse_width_ns: int
    pulse_repeat: int = 1
    pulse_deadtime_ms: int = 10
    arm_timeout_min: int = 1
    mute: bool = True


@router.post("/arm")
async def arm() -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/disarm")
async def disarm() -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/pulse")
async def pulse(req: PulseRequest) -> dict:
    """Fire one or more pulses. Requires ArmGate to be armed."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/config")
async def configure(req: ConfigRequest) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
