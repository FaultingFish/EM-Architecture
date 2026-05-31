"""Device discovery + connection lifecycle."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from emfi_protocol.devices import DeviceStatus as DeviceStatusModel

from control.deps import (
    ADAPTER_ATTR,
    DEVICE_NAMES,
    AppContext,
    call_adapter,
    call_subprocess_adapter,
    get_ctx,
)
from control.ports import list_ports, pick_port

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


def _device_status(ctx: AppContext, name: str) -> Dict[str, Any]:
    adapter = ctx.adapter_for(name)
    ds = ctx.state.devices.get(name)
    status: Dict[str, Any] = {
        "name": name,
        "available": True,
        "connected": adapter.connected,
        "port": getattr(adapter, "_port", None),
        "label": ds.label if ds else None,
        "last_error": ds.last_error if ds else None,
        "busy": ctx.workers.get(name).busy if name != "xds110" else False,
    }
    if name == "chipshouter":
        last_fault = getattr(adapter, "last_fault", None)
        status["fault_names"] = last_fault["names"] if last_fault else None
    return status


@router.get("")
def list_devices(ctx: AppContext = Depends(get_ctx)) -> Dict[str, Any]:
    """List discovered serial devices with classification guesses."""
    known = ctx.config.get("known_devices", default={})
    ports = list_ports(known)
    device_statuses = [_device_status(ctx, name) for name in DEVICE_NAMES]
    return {"ports": ports, "devices": device_statuses}


@router.get("/chipshouter/faults")
async def chipshouter_faults(ctx: AppContext = Depends(get_ctx)) -> Dict[str, Any]:
    """Return the ChipSHOUTER's last latched fault + live current faults.

    Shape: ``{"last_fault": {"ts", "names", "raw"} | None,
              "current": [names], "connected": bool}``.
    """
    return ctx.shouter.get_faults()


# ----------------------------------------------------------------------
# Scaffold power rails
#
# Scaffold has two independently-switchable 3.3 V supplies on the board:
#   - DUT      → the MSPM0L2228 target socket            (UI label: slot 1)
#   - Platform → daughterboard / aux header              (UI label: slot 2)
# Both run through the FastAPI scaffold DeviceWorker for serial safety.
# ----------------------------------------------------------------------

_RAILS = ("dut", "platform", "all")


class _PowerSetRequest(BaseModel):
    rail: str = Field(..., description="One of: dut, platform, all")
    on: bool


class _PowerCycleRequest(BaseModel):
    rail: str = Field(..., description="One of: dut, platform, all")
    off_time: float = Field(0.05, ge=0.0, le=5.0, description="Seconds OFF before re-energising")


def _broadcast_power(ctx: AppContext, state: Dict[str, bool]) -> None:
    ctx.broadcast("scaffold_power", state)


@router.get("/scaffold/power")
async def scaffold_power_get(ctx: AppContext = Depends(get_ctx)) -> Dict[str, bool]:
    """Read the live state of both Scaffold power rails."""
    worker = ctx.workers.get("scaffold")
    state = await call_adapter(worker, ctx.scaffold.power_state)
    return state


@router.post("/scaffold/power")
async def scaffold_power_set(
    req: _PowerSetRequest, ctx: AppContext = Depends(get_ctx)
) -> Dict[str, bool]:
    """Enable or disable a Scaffold power rail."""
    if req.rail not in _RAILS:
        raise HTTPException(status_code=400, detail=f"rail must be one of {_RAILS}")
    worker = ctx.workers.get("scaffold")
    if req.rail == "dut":
        await call_adapter(worker, ctx.scaffold.dut_power, req.on)
    elif req.rail == "platform":
        await call_adapter(worker, ctx.scaffold.platform_power, req.on)
    else:
        await call_adapter(worker, ctx.scaffold.dut_power, req.on)
        await call_adapter(worker, ctx.scaffold.platform_power, req.on)
    state = await call_adapter(worker, ctx.scaffold.power_state)
    _broadcast_power(ctx, state)
    LOGGER.info("Scaffold power set: rail=%s on=%s -> %s", req.rail, req.on, state)
    return state


@router.post("/scaffold/power_cycle")
async def scaffold_power_cycle(
    req: _PowerCycleRequest, ctx: AppContext = Depends(get_ctx)
) -> Dict[str, bool]:
    """Power-cycle a Scaffold rail (or both)."""
    if req.rail not in _RAILS:
        raise HTTPException(status_code=400, detail=f"rail must be one of {_RAILS}")
    worker = ctx.workers.get("scaffold")
    if req.rail == "dut":
        await call_adapter(worker, ctx.scaffold.dut_power_cycle, req.off_time)
    elif req.rail == "platform":
        await call_adapter(worker, ctx.scaffold.platform_power_cycle, req.off_time)
    else:
        await call_adapter(worker, ctx.scaffold.all_power_cycle, req.off_time)
    state = await call_adapter(worker, ctx.scaffold.power_state)
    _broadcast_power(ctx, state)
    LOGGER.info("Scaffold power cycled: rail=%s off_time=%.3fs -> %s", req.rail, req.off_time, state)
    return state


@router.post("/{name}/connect")
async def connect(name: str, ctx: AppContext = Depends(get_ctx)) -> Dict[str, Any]:
    """Open the serial port for a device."""
    if name not in DEVICE_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {name}")

    adapter = ctx.adapter_for(name)
    known = ctx.config.get("known_devices", default={})
    overrides = ctx.config.get("ports", default={})
    ports = list_ports(known)
    port = pick_port(name, ports, overrides.get(f"{name}_override"))

    if name == "xds110":
        await call_subprocess_adapter(adapter.connect, port)
    else:
        worker = ctx.workers.get(name)
        await call_adapter(worker, adapter.connect, port)

    ds = ctx.state.devices.get(name)
    if ds:
        ds.connected = True
        ds.port = port
        ds.last_error = None

    status = _device_status(ctx, name)
    ctx.broadcast("device_status", status)
    LOGGER.info("Device %s connected on %s", name, port)
    return status


@router.post("/{name}/disconnect")
async def disconnect(name: str, ctx: AppContext = Depends(get_ctx)) -> Dict[str, Any]:
    if name not in DEVICE_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {name}")

    adapter = ctx.adapter_for(name)

    if name == "xds110":
        await call_subprocess_adapter(adapter.disconnect)
    else:
        worker = ctx.workers.get(name)
        await call_adapter(worker, adapter.disconnect)

    ds = ctx.state.devices.get(name)
    if ds:
        ds.connected = False
        ds.port = None

    status = _device_status(ctx, name)
    ctx.broadcast("device_status", status)
    LOGGER.info("Device %s disconnected", name)
    return status
