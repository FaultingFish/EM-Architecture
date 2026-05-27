"""FastAPI entrypoint for Control."""

from __future__ import annotations

from fastapi import FastAPI
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


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMFI Control",
        version="0.1.0",
        description="Hardware-singleton service for the lab rig.",
    )

    # LAN-only deployment — auth is out of scope. Permit any origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
