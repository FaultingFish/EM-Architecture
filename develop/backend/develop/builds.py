"""Firmware build pipeline.

Reads project.toml to determine language, then invokes the right toolchain:
- language=c   →  `make all` in the project root
- language=rust → `cargo build --release --target thumbv8m.main-none-eabi`

Produces builds/<sha>/ with elf, bin, lst, symbols.json, build.log.
The SHA is computed from source-tree + toolchain versions for determinism.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncIterator

from emfi_protocol.projects import BuildArtifact

log = logging.getLogger(__name__)


async def build(project_id: str, version: str | None = None) -> BuildArtifact:
    """Run the project's build and capture artifacts.

    Yields log lines via the WebSocket broadcaster while running.
    """
    log.info("Starting build for project=%s version=%s", project_id, version)
    raise NotImplementedError("builds.build")


def compute_sha(project_dir: Path) -> str:
    """Deterministic hash of (source tree + toolchain versions)."""
    log.debug("Computing SHA for %s", project_dir)
    raise NotImplementedError("builds.compute_sha")


async def stream_build_log(project_id: str, sha: str) -> AsyncIterator[str]:
    log.debug("Streaming build log for project=%s sha=%s", project_id, sha)
    raise NotImplementedError("builds.stream_build_log")
