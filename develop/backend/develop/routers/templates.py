"""Template listing endpoint."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

log = logging.getLogger(__name__)

router = APIRouter(tags=["templates"])


@router.get("/templates")
async def list_templates() -> List[dict]:
    """List available project templates (c_ti_hal, rust_b01lers, etc.)."""
    log.debug("GET /templates")
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
