"""FastAPI entrypoint for Develop.

Serves both REST/WS for the SvelteKit frontend (in dev), and the built
frontend via StaticFiles (in production).
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from develop.config import projects_root, templates_root
from develop.logging_config import setup_logging
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

log_file = setup_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Develop service starting up")
    log.info("Log file: %s", log_file)
    log.info("Projects root: %s", projects_root())
    log.info("Templates root: %s", templates_root())

    static_dir = Path(__file__).parent.parent.parent / "frontend" / "build"
    if static_dir.exists():
        log.info("Serving built frontend from %s", static_dir)
    else:
        log.info("No built frontend at %s — run 'npm run build' in frontend/", static_dir)

    yield

    log.info("Develop service shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMFI Develop",
        version="0.1.0",
        description="Firmware project management, builds, disassembly, agent.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        log.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

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
