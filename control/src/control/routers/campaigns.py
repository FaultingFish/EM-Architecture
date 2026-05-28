"""Campaign lifecycle endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from emfi_protocol.campaigns import Campaign, CampaignStatus

from control.deps import AppContext, get_ctx

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _count_sweep_points(sweep) -> int:
    count = 1
    for dim in (sweep.delay_us, sweep.pulse_width_ns, sweep.voltage_v):
        if dim is not None and dim.step > 0:
            steps = int((dim.stop - dim.start) / dim.step) + 1
            count *= max(1, steps)
    count *= max(1, sweep.attempts_per_point)
    return count


def _count_grid_points(grid) -> int:
    x_steps = int(round((grid.top_right[0] - grid.origin[0]) / grid.step_size_mm)) + 1
    y_steps = int(round((grid.top_right[1] - grid.origin[1]) / grid.step_size_mm)) + 1
    z_step = grid.z_step_mm if grid.z_step_mm > 0 else 1
    z_range = grid.z_max_mm - grid.z_min_mm
    z_steps = int(round(z_range / z_step)) + 1 if z_range > 0 else 1
    return max(1, x_steps) * max(1, y_steps) * max(1, z_steps)


@router.post("", response_model=CampaignStatus)
async def start(campaign: Campaign, ctx: AppContext = Depends(get_ctx)) -> CampaignStatus:
    """Start a campaign. Returns immediately with the assigned ID."""
    if campaign.id is None:
        campaign.id = str(uuid.uuid4())
    if campaign.created_at is None:
        campaign.created_at = datetime.now(timezone.utc)

    total = _count_grid_points(campaign.grid) * _count_sweep_points(campaign.sweep)

    status = CampaignStatus(
        campaign_id=campaign.id,
        active=True,
        completed_attempts=0,
        total_attempts=total,
        started_at=datetime.now(timezone.utc),
    )
    ctx.campaigns[campaign.id] = status

    async def _run() -> None:
        try:
            await ctx.orchestrator.run_campaign(campaign, status)
        except Exception:
            LOGGER.exception("Campaign %s failed", campaign.id)
        finally:
            status.active = False
            status.finished_at = datetime.now(timezone.utc)

    asyncio.create_task(_run())
    LOGGER.info("Campaign %s started (%d total attempts)", campaign.id, total)
    return status


@router.get("", response_model=List[CampaignStatus])
async def list_all(ctx: AppContext = Depends(get_ctx)) -> List[CampaignStatus]:
    return list(ctx.campaigns.values())


@router.get("/{campaign_id}", response_model=CampaignStatus)
async def get_one(campaign_id: str, ctx: AppContext = Depends(get_ctx)) -> CampaignStatus:
    if campaign_id not in ctx.campaigns:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return ctx.campaigns[campaign_id]


@router.post("/{campaign_id}/stop")
async def stop(campaign_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    if campaign_id not in ctx.campaigns:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    ctx.stop_flag.set()
    LOGGER.info("Campaign %s stop requested", campaign_id)
    return {"ok": True, "campaign_id": campaign_id}
