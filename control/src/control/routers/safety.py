"""ARM gate endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from emfi_protocol.devices import ArmState

router = APIRouter(tags=["safety"])


@router.post("/arm", response_model=ArmState)
async def arm() -> ArmState:
    """Engage the ARM gate. UI should require a hold gesture to call this."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/disarm", response_model=ArmState)
async def disarm() -> ArmState:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/arm_state", response_model=ArmState)
async def arm_state() -> ArmState:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
