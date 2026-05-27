"""FastAPI entrypoint for Develop.

Serves both REST/WS for the SvelteKit frontend (in dev), and the built
frontend via StaticFiles (in production).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from develop.routers import (
    agent,
    artifacts,
    builds,
    disassembly,
    git,
    projects,
    targets,
    templates,
    ws,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMFI Develop",
        version="0.1.0",
        description="Firmware project management, builds, disassembly, agent.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router)
    app.include_router(builds.router)
    app.include_router(artifacts.router)
    app.include_router(disassembly.router)
    app.include_router(git.router)
    app.include_router(targets.router)
    app.include_router(templates.router)
    app.include_router(agent.router)
    app.include_router(ws.router)

    # Serve the built SvelteKit frontend if present.
    static_dir = Path(__file__).parent.parent.parent / "frontend" / "build"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")

    return app


app = create_app()
