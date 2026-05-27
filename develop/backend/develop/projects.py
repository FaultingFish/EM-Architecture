"""Project CRUD over ~/emfi-projects/<id>/."""

from __future__ import annotations

from pathlib import Path
from typing import List

from emfi_protocol.projects import Project

from develop.config import projects_root


def list_projects() -> List[Project]:
    """Scan ~/emfi-projects/ for valid projects."""
    raise NotImplementedError("projects.list_projects")


def get_project(project_id: str) -> Project:
    raise NotImplementedError("projects.get_project")


def create_project(name: str, template: str, language: str, hal: str) -> Project:
    """Copy a template into ~/emfi-projects/<slug>/ and git init."""
    raise NotImplementedError("projects.create_project")


def delete_project(project_id: str) -> None:
    """Soft delete: move to ~/emfi-projects/.trash/<id>-<ts>/."""
    raise NotImplementedError("projects.delete_project")


def project_dir(project_id: str) -> Path:
    return projects_root() / project_id
