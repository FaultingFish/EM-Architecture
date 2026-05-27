"""Project CRUD over ~/emfi-projects/<id>/."""

from __future__ import annotations

import logging
import os
import re
import shutil
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from emfi_protocol.projects import Project

from develop import git_ops
from develop.config import projects_root, templates_root

log = logging.getLogger(__name__)


class ProjectNotFoundError(Exception):
    pass


class ProjectExistsError(Exception):
    pass


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _parse_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_project(project_path: Path) -> Project:
    toml_path = project_path / "project.toml"
    if not toml_path.exists():
        raise ProjectNotFoundError(f"No project.toml in {project_path}")

    data = _parse_toml(toml_path)

    try:
        versions = git_ops.list_tags(project_path)
    except git_ops.GitError:
        versions = []

    return Project(
        id=project_path.name,
        name=data.get("name", project_path.name),
        language=data.get("language", "c"),
        target=data.get("target", "mspm0l2228"),
        hal=data.get("hal", "ti"),
        created_at=datetime.fromisoformat(data["created_at"])
        if "created_at" in data
        else datetime.now(timezone.utc),
        description=data.get("description"),
        versions=versions,
    )


def project_dir(project_id: str) -> Path:
    return projects_root() / project_id


def list_projects() -> List[Project]:
    """Scan ~/emfi-projects/ for valid projects."""
    root = projects_root()
    log.info("Listing projects in %s", root)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        return []

    projects = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        toml_path = entry / "project.toml"
        if not toml_path.exists():
            log.debug("Skipping %s — no project.toml", entry.name)
            continue
        try:
            projects.append(_load_project(entry))
        except Exception as e:
            log.warning("Skipping %s — error loading: %s", entry.name, e)
    return projects


def get_project(project_id: str) -> Project:
    log.info("Loading project %s", project_id)
    p = project_dir(project_id)
    if not p.exists():
        raise ProjectNotFoundError(f"Project {project_id!r} not found")
    return _load_project(p)


def create_project(
    name: str, template: str, language: str, hal: str, description: str = ""
) -> Project:
    """Copy a template into ~/emfi-projects/<slug>/ and git init."""
    slug = _slugify(name)
    dest = project_dir(slug)

    log.info(
        "Creating project name=%s slug=%s template=%s lang=%s hal=%s",
        name, slug, template, language, hal,
    )

    if dest.exists():
        raise ProjectExistsError(f"Project directory {dest} already exists")

    template_dir = templates_root() / template
    if not template_dir.exists():
        raise FileNotFoundError(f"Template {template!r} not found at {template_dir}")

    projects_root().mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, dest)

    # Render project.toml from template
    tmpl_file = dest / "project.toml.template"
    now = datetime.now(timezone.utc).isoformat()
    if tmpl_file.exists():
        content = tmpl_file.read_text()
        content = content.replace("{{ project_name }}", name)
        content = content.replace("{{ created_at }}", now)
        content = content.replace("{{ description }}", description or "")
        (dest / "project.toml").write_text(content)
        tmpl_file.unlink()
    else:
        (dest / "project.toml").write_text(
            f'name = "{name}"\n'
            f'language = "{language}"\n'
            f'target = "mspm0l2228"\n'
            f'hal = "{hal}"\n'
            f'created_at = "{now}"\n'
            f'description = "{description}"\n'
        )

    git_ops.init(dest)
    git_ops.commit(dest, "Initial commit from template")

    return _load_project(dest)


def delete_project(project_id: str) -> None:
    """Soft delete: move to ~/emfi-projects/.trash/<id>-<ts>/."""
    p = project_dir(project_id)
    if not p.exists():
        raise ProjectNotFoundError(f"Project {project_id!r} not found")

    trash = projects_root() / ".trash"
    trash.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    dest = trash / f"{project_id}-{ts}"

    log.warning("Soft-deleting project %s -> %s", project_id, dest)
    shutil.move(str(p), str(dest))


def file_tree(project_id: str) -> dict:
    """Walk the project directory, return a nested dict tree."""
    root = project_dir(project_id)
    if not root.exists():
        raise ProjectNotFoundError(f"Project {project_id!r} not found")

    skip = {".git", "builds", "__pycache__", "target"}

    def _walk(dirpath: Path) -> dict:
        children = []
        try:
            entries = sorted(dirpath.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return {"name": dirpath.name, "type": "dir", "path": "", "children": []}

        for entry in entries:
            if entry.name in skip or entry.name.startswith("."):
                continue
            rel = str(entry.relative_to(root))
            if entry.is_dir():
                children.append(_walk(entry))
            else:
                children.append({"name": entry.name, "type": "file", "path": rel})
        return {
            "name": dirpath.name,
            "type": "dir",
            "path": str(dirpath.relative_to(root)) if dirpath != root else "",
            "children": children,
        }

    return _walk(root)


def read_file(project_id: str, relative_path: str) -> str:
    """Read a file's contents, with path-traversal prevention."""
    root = project_dir(project_id)
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise PermissionError("Path traversal denied")
    if not target.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")
    log.debug("Reading %s in project %s", relative_path, project_id)
    return target.read_text(errors="replace")


def write_file(project_id: str, relative_path: str, contents: str) -> None:
    """Write file contents, with path-traversal prevention."""
    root = project_dir(project_id)
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise PermissionError("Path traversal denied")
    target.parent.mkdir(parents=True, exist_ok=True)
    log.info("Writing %s in project %s (%d bytes)", relative_path, project_id, len(contents))
    target.write_text(contents)
