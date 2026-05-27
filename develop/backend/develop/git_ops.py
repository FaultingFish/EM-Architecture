"""Subprocess git wrapper for per-project repos."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True)


def commit(repo: Path, message: str) -> str:
    """Stage all changes and commit. Returns the commit SHA."""
    raise NotImplementedError("git_ops.commit")


def tag(repo: Path, name: str) -> None:
    raise NotImplementedError("git_ops.tag")


def list_tags(repo: Path) -> List[str]:
    raise NotImplementedError("git_ops.list_tags")


def log(repo: Path, limit: int = 50) -> List[dict]:
    raise NotImplementedError("git_ops.log")
