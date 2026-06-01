from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from emfi_protocol.campaigns import Campaign, GridParams, SweepParams, SweepRange

from control.routers.campaigns import _preflight
from control.state import AppState, DeviceStatus


class _Config:
    def get(self, *path: str, default: Any = None) -> Any:
        if path == ("safety",):
            return {
                "max_voltage_v": 350,
                "max_pulses_per_sec": 10,
                "max_attempts_per_location": 1000,
            }
        return default


@dataclass
class _Context:
    state: AppState
    config: _Config = field(default_factory=_Config)
    campaigns: dict[str, Any] = field(default_factory=dict)


def _campaign(**overrides) -> Campaign:
    data = {
        "name": "test",
        "project_id": "purpleboardtest",
        "build_sha": "abc123",
        "grid": GridParams(
            origin=(0.0, 0.0),
            top_right=(1.0, 1.0),
            step_size_mm=1.0,
            z_min_mm=0.0,
            z_max_mm=0.0,
            z_step_mm=0.1,
        ),
        "sweep": SweepParams(
            delay_us=SweepRange(start=1.0, stop=3.0, step=1.0),
            attempts_per_point=2,
        ),
        "trigger_mode": "software",
        "shouter_voltage": 250,
    }
    data.update(overrides)
    return Campaign(**data)


def _state(*connected: str, armed: bool = True) -> AppState:
    names = ("chipshover", "chipshouter", "scaffold", "xds110")
    return AppState(
        armed=armed,
        devices={
            name: DeviceStatus(name=name, connected=name in connected)
            for name in names
        },
    )


def test_preflight_ok_counts_budget():
    ctx = _Context(_state("chipshover", "chipshouter", "scaffold", "xds110"))

    result = _preflight(_campaign(), ctx)

    assert result.ok is True
    assert result.grid_points == 4
    assert result.sweep_points == 6
    assert result.total_attempts == 24
    assert result.blockers == []


def test_preflight_blocks_missing_required_device():
    ctx = _Context(_state("chipshover", "scaffold"))

    result = _preflight(_campaign(), ctx)

    assert result.ok is False
    assert "required device is not connected: chipshouter" in result.blockers


def test_preflight_blocks_voltage_over_safety_limit():
    ctx = _Context(_state("chipshover", "chipshouter", "scaffold"))

    result = _preflight(_campaign(shouter_voltage=500), ctx)

    assert result.ok is False
    assert any("exceeds safety max_voltage_v" in b for b in result.blockers)


def test_preflight_warns_when_not_armed_or_pinned():
    ctx = _Context(_state("chipshover", "chipshouter", "scaffold", armed=False))

    result = _preflight(_campaign(build_sha=None), ctx)

    assert result.ok is True
    assert any("not armed" in w for w in result.warnings)
    assert any("no pinned build_sha" in w for w in result.warnings)
