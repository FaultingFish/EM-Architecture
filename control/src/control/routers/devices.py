"""Device discovery + connection lifecycle."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
def list_devices() -> List[dict]:
    """List discovered serial devices with classification guesses."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/{name}/connect")
def connect(name: str) -> dict:
    """Open the serial port for `name` (one of chipshover/chipshouter/scaffold/xds110)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/{name}/disconnect")
def disconnect(name: str) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
