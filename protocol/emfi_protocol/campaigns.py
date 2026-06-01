"""Campaign / sweep / grid configuration models."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class GridParams(BaseModel):
    """3D rectangular scan grid in logical (origin-relative) coordinates."""

    origin: Tuple[float, float] = Field(..., description="Bottom-left XY in mm")
    top_right: Tuple[float, float] = Field(..., description="Top-right XY in mm")
    step_size_mm: float = Field(1.0, gt=0)
    z_min_mm: float = 0.0
    z_max_mm: float = 0.5
    z_step_mm: float = Field(0.1, gt=0)


class SweepRange(BaseModel):
    """Inclusive numerical sweep with explicit step.

    Set start == stop to pin a single value. Use null to skip this dimension.
    """

    start: float
    stop: float
    step: float = Field(..., gt=0)


class SweepParams(BaseModel):
    """Parameters varied across attempts at each grid point."""

    delay_us: Optional[SweepRange] = None
    pulse_width_ns: Optional[SweepRange] = None
    voltage_v: Optional[SweepRange] = None
    attempts_per_point: int = Field(1, ge=1)


class StopConditions(BaseModel):
    """Optional policies that stop an otherwise valid campaign early."""

    max_glitches: Optional[int] = Field(
        None,
        ge=1,
        description="Stop the campaign after this many glitch outcomes",
    )
    stop_on_first_crash: bool = Field(
        False,
        description="Stop the campaign after the first crash outcome",
    )
    max_runtime_seconds: Optional[float] = Field(
        None,
        gt=0,
        description="Stop the campaign once wall-clock runtime reaches this many seconds",
    )


class Campaign(BaseModel):
    """A user-defined glitch campaign."""

    id: Optional[str] = None
    name: str
    created_at: Optional[datetime] = None

    # Firmware reference (resolved by Control via Develop)
    project_id: str
    project_version: Optional[str] = Field(None, description="Git tag or None for current HEAD")
    build_sha: Optional[str] = Field(None, description="Pinned build hash; None = build at start")
    target_pc: Optional[int] = Field(None, description="Annotated target instruction (optional)")

    grid: GridParams
    sweep: SweepParams

    # Shouter config
    trigger_mode: str = Field("software", description="software | one-shot | free-run | disabled")
    shouter_voltage: int = 250
    shouter_pulse_width_ns: int = 80
    shouter_mute: bool = True
    shouter_auto_arm: bool = True

    verdict_timeout_ms: int = 500

    # Optional unattended-run stop policies. Defaults preserve historical
    # behavior: run the full grid/sweep unless a manual stop is requested.
    stop_conditions: Optional[StopConditions] = Field(
        None,
        description="Grouped stop policy fields used by View and automation clients",
    )
    max_glitches: Optional[int] = Field(
        None,
        ge=1,
        description="Legacy top-level alias for stop_conditions.max_glitches",
    )
    stop_on_first_crash: bool = Field(
        False,
        description="Legacy top-level alias for stop_conditions.stop_on_first_crash",
    )
    max_runtime_seconds: Optional[float] = Field(
        None,
        gt=0,
        description="Legacy top-level alias for stop_conditions.max_runtime_seconds",
    )


class CampaignStatus(BaseModel):
    """Run-time progress."""

    campaign_id: str
    active: bool
    completed_attempts: int
    total_attempts: int
    current_position: Optional[Tuple[float, float, float]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_outcome: Optional[str] = None
