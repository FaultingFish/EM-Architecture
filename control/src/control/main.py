"""FastAPI entrypoint for Control."""

from __future__ import annotations

import logging
import logging.handlers
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from control.routers import (
    campaigns,
    devices,
    motion,
    runs,
    safety,
    shouter,
    target,
    ws,
)

LOGGER = logging.getLogger("control")

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _default_log_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "share"))
    return base / "emfi-control" / "logs"


def setup_logging() -> Path:
    """Configure root logger: console + rotating file.

    Returns the log file path so start.sh can display it.
    """
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log_path = setup_logging()
    LOGGER.info("Control starting — log file: %s", log_path)
    LOGGER.info("API docs: http://%s:%s/docs",
                os.environ.get("CONTROL_HOST", "0.0.0.0"),
                os.environ.get("CONTROL_PORT", "8001"))
    yield
    LOGGER.info("Control shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMFI Control",
        version="0.1.0",
        description="Hardware-singleton service for the lab rig.",
        lifespan=lifespan,
    )

    # LAN-only deployment — auth is out of scope. Permit any origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        LOGGER.info("%s %s", request.method, request.url.path)
        response: Response = await call_next(request)
        if response.status_code >= 400:
            LOGGER.warning("%s %s -> %d", request.method, request.url.path, response.status_code)
        return response

    app.include_router(devices.router)
    app.include_router(motion.router)
    app.include_router(shouter.router)
    app.include_router(target.router)
    app.include_router(campaigns.router)
    app.include_router(runs.router)
    app.include_router(safety.router)
    app.include_router(ws.router)

    return app


app = create_app()
