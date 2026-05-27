"""Central application context and FastAPI dependency helpers.

All shared singletons live on AppContext, created once in the lifespan
and accessed by routers via ``get_ctx(request)``.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request

from control.adapters.chipshouter import ChipShouterAdapter
from control.adapters.chipshover import ChipShoverAdapter
from control.adapters.scaffold import ScaffoldAdapter
from control.adapters.xds110 import XDS110Adapter
from control.config import Config
from control.logbook import Logbook, default_log_dir
from control.orchestrator import Orchestrator
from control.safety import ArmGate, RateLimiter, StopFlag
from control.state import AppState, Broadcaster, DeviceStatus
from control.workers import DeviceWorker, WorkerRegistry

LOGGER = logging.getLogger(__name__)

DEVICE_NAMES = ("chipshover", "chipshouter", "scaffold", "xds110")

ADAPTER_ATTR = {
    "chipshover": "shover",
    "chipshouter": "shouter",
    "scaffold": "scaffold",
    "xds110": "xds110",
}


@dataclass
class AppContext:
    config: Config
    state: AppState
    broadcaster: Broadcaster
    arm_gate: ArmGate
    stop_flag: StopFlag
    rate_limiter: RateLimiter
    logbook: Logbook
    workers: WorkerRegistry
    shover: ChipShoverAdapter
    shouter: ChipShouterAdapter
    scaffold: ScaffoldAdapter
    xds110: XDS110Adapter
    orchestrator: Orchestrator
    loop: Optional[asyncio.AbstractEventLoop] = None
    campaigns: Dict[str, Any] = field(default_factory=dict)

    def adapter_for(self, name: str) -> Any:
        attr = ADAPTER_ATTR.get(name)
        if attr is None:
            raise HTTPException(status_code=404, detail=f"Unknown device: {name}")
        return getattr(self, attr)

    def broadcast(self, topic: str, payload: Dict[str, Any]) -> None:
        msg: Dict[str, Any] = {"type": "event", "topic": topic, "payload": payload}
        if self.loop is not None and self.loop.is_running():
            self.broadcaster.broadcast_threadsafe(self.loop, msg)
        else:
            self.broadcaster.broadcast(msg)

    def broadcast_state(self) -> None:
        self.broadcast("state", self.state.snapshot())


def build_context() -> AppContext:
    config = Config()

    state = AppState(
        devices={
            name: DeviceStatus(name=name)
            for name in DEVICE_NAMES
        },
    )

    broadcaster = Broadcaster()

    auto_disarm_min = config.get("safety", "auto_disarm_minutes", default=5)
    arm_gate = ArmGate(auto_disarm_seconds=float(auto_disarm_min) * 60)

    stop_flag = StopFlag()

    max_pps = config.get("safety", "max_pulses_per_sec", default=10)
    rate_limiter = RateLimiter("pulse", max_per_sec=float(max_pps))

    logbook = Logbook(default_log_dir())
    workers = WorkerRegistry()

    shover = ChipShoverAdapter()
    shouter = ChipShouterAdapter()
    scaffold = ScaffoldAdapter()
    xds110 = XDS110Adapter(
        dslite_bin=os.environ.get("DSLITE_BIN") or config.get("programmer", "dslite_bin"),
        openocd_bin=os.environ.get("OPENOCD_BIN") or config.get("programmer", "openocd_bin"),
        openocd_config=config.get("programmer", "openocd_config"),
    )

    ctx = AppContext(
        config=config,
        state=state,
        broadcaster=broadcaster,
        arm_gate=arm_gate,
        stop_flag=stop_flag,
        rate_limiter=rate_limiter,
        logbook=logbook,
        workers=workers,
        shover=shover,
        shouter=shouter,
        scaffold=scaffold,
        xds110=xds110,
        orchestrator=None,  # type: ignore[arg-type]
    )

    orchestrator = Orchestrator(
        state=state,
        arm_gate=arm_gate,
        stop_flag=stop_flag,
        rate_limiter=rate_limiter,
        logbook=logbook,
        shover=shover,
        shouter=shouter,
        scaffold=scaffold,
        broadcast=ctx.broadcast,
    )
    ctx.orchestrator = orchestrator

    def _on_arm_change(armed: bool) -> None:
        state.armed = armed
        remaining = None
        if armed:
            remaining = arm_gate.auto_disarm_seconds
        ctx.broadcast("arm", {
            "armed": armed,
            "seconds_until_auto_disarm": remaining,
        })

    arm_gate.on_change = _on_arm_change

    LOGGER.info("AppContext built — %d devices registered", len(DEVICE_NAMES))
    return ctx


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


async def call_adapter(worker: DeviceWorker, fn: Callable, *args: Any, **kwargs: Any) -> Any:
    try:
        return await worker.call(fn, *args, **kwargs)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=f"Adapter not implemented: {exc}")
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))


async def call_subprocess_adapter(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=f"Adapter not implemented: {exc}")
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
