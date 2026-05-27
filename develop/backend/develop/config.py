"""Develop service config."""

from __future__ import annotations

import os
from pathlib import Path


def projects_root() -> Path:
    p = os.environ.get("EMFI_PROJECTS_ROOT")
    return Path(p) if p else (Path.home() / "emfi-projects")


def templates_root() -> Path:
    return Path(__file__).parent / "templates"


def claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN", "claude")


def arm_gcc_bin() -> str:
    return os.environ.get("ARM_GCC_BIN", "arm-none-eabi-gcc")


def arm_objdump_bin() -> str:
    return os.environ.get("ARM_OBJDUMP_BIN", "arm-none-eabi-objdump")


def cargo_bin() -> str:
    return os.environ.get("CARGO_BIN", "cargo")
