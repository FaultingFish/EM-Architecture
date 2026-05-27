"""Firmware build pipeline.

Reads project.toml to determine language, then invokes the right toolchain:
- language=c   →  `make all` in the project root
- language=rust → `cargo build --release --target thumbv8m.main-none-eabi`

Produces builds/<sha>/ with elf, bin, lst, symbols.json, build.log.
The SHA is computed from source-tree + toolchain versions for determinism.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, List, Optional

from emfi_protocol.projects import BuildArtifact
from emfi_protocol.ws_events import WsTopic

from develop.broadcaster import broadcaster
from develop.config import arm_gcc_bin, arm_objcopy_bin, arm_objdump_bin, cargo_bin
from develop.projects import project_dir

log = logging.getLogger(__name__)


class ToolchainNotFoundError(Exception):
    pass


def _read_language(proj_dir: Path) -> str:
    toml_path = proj_dir / "project.toml"
    with open(toml_path, "rb") as f:
        return tomllib.load(f).get("language", "c")


def _toolchain_version(binary: str) -> str:
    try:
        r = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()[:200]
    except FileNotFoundError:
        return "not-found"


def compute_sha(proj_dir: Path) -> str:
    """Deterministic hash of (source tree + toolchain versions)."""
    h = hashlib.sha256()

    src = proj_dir / "src"
    if src.exists():
        for f in sorted(src.rglob("*")):
            if f.is_file():
                h.update(str(f.relative_to(proj_dir)).encode())
                h.update(f.read_bytes())

    for extra in ["Makefile", "Cargo.toml", "linker.ld", "project.toml"]:
        p = proj_dir / extra
        if p.exists():
            h.update(p.read_bytes())

    lang = _read_language(proj_dir)
    if lang == "c":
        h.update(_toolchain_version(arm_gcc_bin()).encode())
    else:
        h.update(_toolchain_version(cargo_bin()).encode())

    return h.hexdigest()[:12]


def list_build_artifacts(project_id: str) -> List[BuildArtifact]:
    builds_dir = project_dir(project_id) / "builds"
    if not builds_dir.exists():
        return []
    artifacts = []
    for entry in sorted(builds_dir.iterdir(), reverse=True):
        meta_path = entry / "build_meta.json"
        if meta_path.exists():
            try:
                artifacts.append(BuildArtifact(**json.loads(meta_path.read_text())))
            except Exception as e:
                log.warning("Skipping build %s: %s", entry.name, e)
    return artifacts


def get_build_artifact(project_id: str, sha: str) -> Optional[BuildArtifact]:
    build_dir = project_dir(project_id) / "builds" / sha
    meta_path = build_dir / "build_meta.json"
    if not meta_path.exists():
        return None
    return BuildArtifact(**json.loads(meta_path.read_text()))


async def build(project_id: str, version: str | None = None) -> BuildArtifact:
    """Run the project's build and capture artifacts."""
    proj_path = project_dir(project_id)
    if not proj_path.exists():
        raise FileNotFoundError(f"Project {project_id!r} not found")

    lang = _read_language(proj_path)
    sha = compute_sha(proj_path)

    build_dir = proj_path / "builds" / sha
    meta_path = build_dir / "build_meta.json"
    if meta_path.exists():
        log.info("Build %s already cached for project=%s", sha, project_id)
        return BuildArtifact(**json.loads(meta_path.read_text()))

    log.info("Starting build for project=%s lang=%s sha=%s", project_id, lang, sha)
    await broadcaster.broadcast(WsTopic.BUILD_STATUS, {
        "project_id": project_id, "sha": sha, "phase": "starting",
    })

    if lang == "c":
        if not shutil.which(arm_gcc_bin()):
            raise ToolchainNotFoundError(
                f"{arm_gcc_bin()} not found on PATH. "
                "Install: apt install gcc-arm-none-eabi"
            )
        cmd = ["make", "all"]
    elif lang == "rust":
        if not shutil.which(cargo_bin()):
            raise ToolchainNotFoundError(
                f"{cargo_bin()} not found on PATH. "
                "Install: rustup + rustup target add thumbv8m.main-none-eabi"
            )
        cmd = [cargo_bin(), "build", "--release", "--target", "thumbv8m.main-none-eabi"]
    else:
        raise ValueError(f"Unknown language: {lang}")

    await broadcaster.broadcast(WsTopic.BUILD_STATUS, {
        "project_id": project_id, "sha": sha, "phase": "compiling",
    })

    log_lines: list[str] = []
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(proj_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async for raw_line in proc.stdout:
        line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
        log_lines.append(line)
        await broadcaster.broadcast(WsTopic.BUILD_LOG, {
            "project_id": project_id, "sha": sha, "line": line,
        })

    await proc.wait()
    success = proc.returncode == 0

    build_dir.mkdir(parents=True, exist_ok=True)

    (build_dir / "build.log").write_text("\n".join(log_lines) + "\n")

    if success:
        await broadcaster.broadcast(WsTopic.BUILD_STATUS, {
            "project_id": project_id, "sha": sha, "phase": "linking",
        })
        _collect_artifacts(proj_path, build_dir, lang)

    phase = "done" if success else "failed"
    await broadcaster.broadcast(WsTopic.BUILD_STATUS, {
        "project_id": project_id, "sha": sha, "phase": phase,
    })

    artifact = BuildArtifact(
        project_id=project_id,
        version=version,
        sha=sha,
        built_at=datetime.now(timezone.utc),
        elf_path=str(build_dir / "firmware.elf"),
        bin_path=str(build_dir / "firmware.bin"),
        listing_path=str(build_dir / "firmware.lst"),
        symbols_path=str(build_dir / "symbols.json"),
        success=success,
        log_tail="\n".join(log_lines[-20:]) if log_lines else None,
    )
    meta_path.write_text(artifact.model_dump_json(indent=2))

    log.info("Build %s for project=%s: %s", sha, project_id, phase)
    return artifact


def _collect_artifacts(proj_path: Path, build_dir: Path, lang: str) -> None:
    """Copy/generate build outputs into builds/<sha>/."""
    if lang == "c":
        for name in ["firmware.elf", "firmware.bin", "firmware.lst"]:
            src = proj_path / name
            if src.exists():
                shutil.copy2(src, build_dir / name)
    elif lang == "rust":
        release_dir = proj_path / "target" / "thumbv8m.main-none-eabi" / "release"
        for f in release_dir.glob("*"):
            if f.suffix == "" and f.is_file() and f.stat().st_size > 0:
                shutil.copy2(f, build_dir / "firmware.elf")
                break

        elf = build_dir / "firmware.elf"
        if elf.exists():
            objcopy = arm_objcopy_bin()
            if shutil.which(objcopy):
                subprocess.run(
                    [objcopy, "-O", "binary", str(elf), str(build_dir / "firmware.bin")],
                    check=False,
                )
            objdump = arm_objdump_bin()
            if shutil.which(objdump):
                result = subprocess.run(
                    [objdump, "-d", "-S", str(elf)],
                    capture_output=True, text=True, check=False,
                )
                if result.returncode == 0:
                    (build_dir / "firmware.lst").write_text(result.stdout)

    (build_dir / "symbols.json").write_text("[]")


async def stream_build_log(project_id: str, sha: str) -> AsyncIterator[str]:
    log_file = project_dir(project_id) / "builds" / sha / "build.log"
    if not log_file.exists():
        return
    for line in log_file.read_text().splitlines():
        yield line
