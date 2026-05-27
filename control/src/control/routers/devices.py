"""Device discovery + connection lifecycle."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

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
    return {
        "name": name,
        "available": True,
        "connected": adapter.connected,
        "port": getattr(adapter, "_port", None),
        "label": ds.label if ds else None,
        "last_error": ds.last_error if ds else None,
        "busy": ctx.workers.get(name).busy if name != "xds110" else False,
    }


@router.get("")
def list_devices(ctx: AppContext = Depends(get_ctx)) -> Dict[str, Any]:
    """List discovered serial devices with classification guesses."""
    known = ctx.config.get("known_devices", default={})
    ports = list_ports(known)
    device_statuses = [_device_status(ctx, name) for name in DEVICE_NAMES]
    return {"ports": ports, "devices": device_statuses}


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
