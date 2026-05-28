"""Logbook query endpoints + replay."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from control.deps import AppContext, get_ctx

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


@router.get("/runs")
async def list_runs(
    campaign: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=10000),
    ctx: AppContext = Depends(get_ctx),
) -> List[Dict[str, Any]]:
    """Query the logbook (backed by SQLite mirror for speed)."""
    entries = ctx.logbook.read(since=since, limit=limit, outcome=outcome)
    if campaign:
        entries = [e for e in entries if e.get("campaign_id") == campaign]
    return entries


@router.get("/runs/{run_id}")
async def get_run(run_id: str, ctx: AppContext = Depends(get_ctx)) -> Dict[str, Any]:
    entry = ctx.logbook.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return entry


@router.get("/heatmap")
async def heatmap(
    campaign: Optional[str] = Query(None),
    z: Optional[float] = Query(None),
    outcome: Optional[str] = Query(
        None, description="Filter to a single outcome; omit for all outcomes"
    ),
    ctx: AppContext = Depends(get_ctx),
) -> List[Dict[str, Any]]:
    """Fault density grouped by (x, y).

    Returns ``[{x, y, counts: {glitch, hang, crash, nothing}}]``. By default
    all outcomes are included so the heatmap is non-empty before any glitch
    lands; pass ``outcome`` to restrict to one bucket.
    """
    return ctx.logbook.heatmap(campaign_id=campaign, z=z, outcome=outcome)


@router.post("/replay/{run_id}")
async def replay(run_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    """Re-execute the exact glitch attempt identified by run_id."""
    ctx.arm_gate.require_armed()
    ctx.rate_limiter.acquire()
    try:
        result = await ctx.orchestrator.replay(run_id)
    except RuntimeError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
    return result
