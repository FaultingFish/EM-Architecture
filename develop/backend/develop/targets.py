"""GlitchTarget CRUD — annotations stored in `targets.json` per project."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from emfi_protocol.projects import GlitchTarget

from develop.projects import project_dir

log = logging.getLogger(__name__)


def targets_file(project_id: str) -> Path:
    return project_dir(project_id) / "targets.json"


def list_targets(project_id: str) -> List[GlitchTarget]:
    log.debug("Listing targets for project=%s", project_id)
    raise NotImplementedError("targets.list_targets")


def add_target(project_id: str, target: GlitchTarget) -> GlitchTarget:
    """Append target to targets.json and commit the change."""
    log.info("Adding target pc=0x%x to project=%s", target.pc_address, project_id)
    raise NotImplementedError("targets.add_target")


def remove_target(project_id: str, pc_address: int) -> None:
    log.info("Removing target pc=0x%x from project=%s", pc_address, project_id)
    raise NotImplementedError("targets.remove_target")
