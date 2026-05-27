"""Subprocess git wrapper for per-project repos."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)


def init(repo: Path) -> None:
    log.info("git init %s", repo)
    subprocess.run(["git", "init"], cwd=repo, check=True)


def commit(repo: Path, message: str) -> str:
    """Stage all changes and commit. Returns the commit SHA."""
    log.info("git commit in %s: %s", repo, message[:80])
    raise NotImplementedError("git_ops.commit")


def tag(repo: Path, name: str) -> None:
    log.info("git tag %s in %s", name, repo)
    raise NotImplementedError("git_ops.tag")


def list_tags(repo: Path) -> List[str]:
    log.debug("git tag -l in %s", repo)
    raise NotImplementedError("git_ops.list_tags")


def log_entries(repo: Path, limit: int = 50) -> List[dict]:
    log.debug("git log -%d in %s", limit, repo)
    raise NotImplementedError("git_ops.log")
