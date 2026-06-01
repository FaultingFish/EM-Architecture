"""FastAPI entrypoint for Control."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from control.auth import install_auth_middleware
from control.deps import ADAPTER_ATTR, DEVICE_NAMES, build_context
from control.routers import (
    campaigns,
    config as config_router,
    devices,
    motion,
    runs,
    safety as safety_router,
    shouter,
    target,
    ws,
)
from control.safety import Disarmed, RateLimited

LOGGER = logging.getLogger("control")

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _default_log_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "share"))
    return base / "emfi-control" / "logs"


def setup_logging() -> Path:
    """Configure root logger: console + rotating file."""
    log_dir = Path(os.environ.get("CONTROL_LOG_DIR", "")) or _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "control.log"

    fmt = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for h in list(root.handlers):
        root.removeHandler(h)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=10_000_000, backupCount=5, encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return log_path


def _auto_connect(ctx) -> None:
    """Connect devices that have a pinned port override in config."""
    from control.deps import AppContext
    overrides = ctx.config.get("ports", default={})
    for device_name in DEVICE_NAMES:
        port = overrides.get(f"{device_name}_override")
        if not port:
            continue
        adapter = ctx.adapter_for(device_name)
        try:
            adapter.connect(port)
            ds = ctx.state.devices.get(device_name)
            if ds:
                ds.connected = True
                ds.port = port
                ds.last_error = None
            LOGGER.info("Auto-connected %s on %s", device_name, port)
        except Exception as exc:
            LOGGER.warning("Auto-connect %s on %s failed: %s", device_name, port, exc)
            ds = ctx.state.devices.get(device_name)
            if ds:
                ds.last_error = str(exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log_path = setup_logging()
    LOGGER.info("Control starting — log file: %s", log_path)

    ctx = build_context()
    app.state.ctx = ctx
    ctx.loop = asyncio.get_running_loop()

    LOGGER.info("API docs: http://%s:%s/docs",
                os.environ.get("CONTROL_HOST", "0.0.0.0"),
                os.environ.get("CONTROL_PORT", "8001"))

    _auto_connect(ctx)

    try:
        yield
    finally:
        LOGGER.info("Control shutting down")
        ctx.stop_flag.set()
        for adapter in (ctx.shover, ctx.shouter, ctx.scaffold, ctx.xds110):
            try:
                adapter.disconnect()
            except Exception:
                pass
        ctx.workers.shutdown_all()


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMFI Control",
        version="0.1.0",
        description="Hardware-singleton service for the lab rig.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_auth_middleware(app)

    @app.exception_handler(Disarmed)
    async def _disarmed(request: Request, exc: Disarmed) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(RateLimited)
    async def _rate_limited(request: Request, exc: RateLimited) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(NotImplementedError)
    async def _not_impl(request: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(status_code=501, content={"detail": f"Not implemented: {exc}"})

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, object]:
        return {"ok": True, "service": "control"}

    @app.get("/readyz", include_in_schema=False, response_model=None)
    async def readyz(request: Request) -> JSONResponse | dict[str, object]:
        ctx = getattr(request.app.state, "ctx", None)
        if ctx is None:
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "ready": False,
                    "service": "control",
                    "reason": "context not initialized",
                },
            )

        config = ctx.config.snapshot()
        ports = config.get("ports", {}) or {}
        state = ctx.state.snapshot()
        devices = state.get("devices", {})

        return {
            "ok": True,
            "ready": True,
            "service": "control",
            "config_path": str(ctx.config.path),
            "log_dir": str(ctx.logbook.log_dir),
            "armed": state.get("armed", False),
            "stop_requested": ctx.stop_flag.is_set(),
            "devices": {
                name: {
                    "connected": status.get("connected", False),
                    "busy": status.get("busy", False),
                    "port_configured": bool(ports.get(f"{name}_override")),
                }
                for name, status in devices.items()
            },
        }

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        LOGGER.info("%s %s", request.method, request.url.path)
        response: Response = await call_next(request)
        if response.status_code >= 400:
            LOGGER.warning("%s %s -> %d", request.method, request.url.path, response.status_code)
        return response

    app.include_router(config_router.router)
    app.include_router(devices.router)
    app.include_router(motion.router)
    app.include_router(shouter.router)
    app.include_router(target.router)
    app.include_router(campaigns.router)
    app.include_router(runs.router)
    app.include_router(safety_router.router)
    app.include_router(ws.router)

    return app


app = create_app()
