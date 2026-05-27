"""Project CRUD over ~/emfi-projects/<id>/."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from emfi_protocol.projects import Project

from develop.config import projects_root

log = logging.getLogger(__name__)


def list_projects() -> List[Project]:
    """Scan ~/emfi-projects/ for valid projects."""
    log.info("Listing projects in %s", projects_root())
    raise NotImplementedError("projects.list_projects")


def get_project(project_id: str) -> Project:
    log.info("Loading project %s", project_id)
    raise NotImplementedError("projects.get_project")


def create_project(name: str, template: str, language: str, hal: str) -> Project:
    """Copy a template into ~/emfi-projects/<slug>/ and git init."""
    log.info("Creating project name=%s template=%s lang=%s hal=%s", name, template, language, hal)
    raise NotImplementedError("projects.create_project")


def delete_project(project_id: str) -> None:
    """Soft delete: move to ~/emfi-projects/.trash/<id>-<ts>/."""
    log.warning("Soft-deleting project %s", project_id)
    raise NotImplementedError("projects.delete_project")


def project_dir(project_id: str) -> Path:
    return projects_root() / project_id
