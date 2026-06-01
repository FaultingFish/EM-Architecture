"""Campaign lifecycle endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from emfi_protocol.campaigns import Campaign, CampaignStatus

from control.deps import AppContext, get_ctx

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignPreflight(BaseModel):
    ok: bool
    total_attempts: int
    grid_points: int
    sweep_points: int
    required_devices: List[str]
    blockers: List[str]
    warnings: List[str]
    estimates: Dict[str, Any]


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


def _connected_devices(ctx: AppContext) -> Dict[str, bool]:
    devices = ctx.state.snapshot().get("devices", {})
    return {
        name: bool(status.get("connected", False))
        for name, status in devices.items()
        if isinstance(status, dict)
    }


def _provenance_blockers(campaign: Campaign, ctx: AppContext) -> List[str]:
    if not campaign.build_sha:
        return []

    flashed = getattr(ctx, "flashed_firmware", None)
    if flashed is None:
        return []

    blockers: List[str] = []
    if flashed.build_sha != campaign.build_sha:
        blockers.append(
            "campaign build_sha "
            f"{campaign.build_sha} does not match flashed DUT build {flashed.build_sha}"
        )
    if flashed.project_id and flashed.project_id != campaign.project_id:
        blockers.append(
            "campaign project_id "
            f"{campaign.project_id} does not match flashed DUT project {flashed.project_id}"
        )
    return blockers


def _preflight(campaign: Campaign, ctx: AppContext) -> CampaignPreflight:
    blockers: List[str] = []
    warnings: List[str] = []

    grid_points = _count_grid_points(campaign.grid)
    sweep_points = _count_sweep_points(campaign.sweep)
    total = grid_points * sweep_points

    if campaign.grid.top_right[0] < campaign.grid.origin[0]:
        blockers.append("grid top_right.x must be >= origin.x")
    if campaign.grid.top_right[1] < campaign.grid.origin[1]:
        blockers.append("grid top_right.y must be >= origin.y")
    if campaign.grid.z_max_mm < campaign.grid.z_min_mm:
        blockers.append("grid z_max_mm must be >= z_min_mm")

    trigger_mode = campaign.trigger_mode
    if trigger_mode not in ("software", "one-shot", "free-run", "disabled"):
        blockers.append("trigger_mode must be one of software, one-shot, free-run, disabled")

    required_devices = ["chipshover", "chipshouter"]
    if trigger_mode in ("one-shot", "free-run"):
        required_devices.append("scaffold")
    elif trigger_mode == "software":
        # Host scripts still commonly use Scaffold for DUT power and verdicts.
        required_devices.append("scaffold")

    connected = _connected_devices(ctx)
    for device in required_devices:
        if not connected.get(device, False):
            blockers.append(f"required device is not connected: {device}")

    if not connected.get("xds110", False):
        warnings.append("xds110 is not connected; flashing/debug will not work until it is connected")
    if not campaign.build_sha:
        warnings.append("campaign has no pinned build_sha; Control may build/use current project state")
    elif getattr(ctx, "flashed_firmware", None) is None:
        warnings.append("no successful DUT flash recorded; cannot verify pinned build_sha")
    blockers.extend(_provenance_blockers(campaign, ctx))
    if ctx.campaigns and any(getattr(c, "active", False) for c in ctx.campaigns.values()):
        blockers.append("another campaign is currently active")
    if not ctx.state.snapshot().get("armed", False):
        warnings.append("system is not armed; campaign start will require arming first")

    safety = ctx.config.get("safety", default={}) or {}
    max_voltage = int(safety.get("max_voltage_v", 0) or 0)
    if max_voltage and campaign.shouter_voltage > max_voltage:
        blockers.append(
            f"shouter_voltage {campaign.shouter_voltage} exceeds safety max_voltage_v {max_voltage}"
        )
    max_attempts_per_location = int(safety.get("max_attempts_per_location", 0) or 0)
    if max_attempts_per_location and sweep_points > max_attempts_per_location:
        blockers.append(
            f"sweep attempts per grid point {sweep_points} exceeds max_attempts_per_location {max_attempts_per_location}"
        )
    max_pps = float(safety.get("max_pulses_per_sec", 0) or 0)
    min_seconds = (total / max_pps) if max_pps > 0 else None

    if total > 100_000:
        warnings.append("campaign exceeds 100000 attempts; confirm runtime and wear before launch")

    return CampaignPreflight(
        ok=not blockers,
        total_attempts=total,
        grid_points=grid_points,
        sweep_points=sweep_points,
        required_devices=required_devices,
        blockers=blockers,
        warnings=warnings,
        estimates={
            "min_runtime_seconds_at_rate_limit": min_seconds,
            "max_pulses_per_sec": max_pps or None,
        },
    )


@router.post("", response_model=CampaignStatus)
async def start(campaign: Campaign, ctx: AppContext = Depends(get_ctx)) -> CampaignStatus:
    """Start a campaign. Returns immediately with the assigned ID."""
    provenance_blockers = _provenance_blockers(campaign, ctx)
    if provenance_blockers:
        raise HTTPException(status_code=409, detail={"blockers": provenance_blockers})

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


@router.post("/preflight", response_model=CampaignPreflight)
async def preflight(campaign: Campaign, ctx: AppContext = Depends(get_ctx)) -> CampaignPreflight:
    """Validate campaign readiness and estimate budget without touching hardware."""
    return _preflight(campaign, ctx)


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
