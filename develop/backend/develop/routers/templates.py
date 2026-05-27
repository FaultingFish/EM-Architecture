"""Template listing endpoint."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["templates"])


@router.get("/templates")
async def list_templates() -> List[dict]:
    """List available project templates (c_ti_hal, rust_b01lers, etc.)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
