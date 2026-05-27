"""GlitchTarget CRUD — annotations stored in `targets.json` per project."""

from __future__ import annotations

from pathlib import Path
from typing import List

from emfi_protocol.projects import GlitchTarget

from develop.projects import project_dir


def targets_file(project_id: str) -> Path:
    return project_dir(project_id) / "targets.json"


def list_targets(project_id: str) -> List[GlitchTarget]:
    raise NotImplementedError("targets.list_targets")


def add_target(project_id: str, target: GlitchTarget) -> GlitchTarget:
    """Append target to targets.json and commit the change."""
    raise NotImplementedError("targets.add_target")


def remove_target(project_id: str, pc_address: int) -> None:
    raise NotImplementedError("targets.remove_target")
