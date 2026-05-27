"""Logbook query endpoints + replay."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from emfi_protocol.runs import AttemptResult

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=List[AttemptResult])
async def list_runs(
    campaign: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=10000),
) -> List[AttemptResult]:
    """Query the logbook (backed by SQLite mirror for speed)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/runs/{run_id}", response_model=AttemptResult)
async def get_run(run_id: str) -> AttemptResult:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/heatmap")
async def heatmap(
    campaign: Optional[str] = Query(None),
    z: Optional[float] = Query(None),
    outcome: str = Query("glitch"),
) -> List[dict]:
    """GROUP BY (x, y) on outcome. Returns [{x, y, count}]."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/replay/{run_id}")
async def replay(run_id: str) -> dict:
    """Re-execute the exact glitch attempt identified by run_id."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
