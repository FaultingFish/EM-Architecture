"""Firmware project, build, and assembly-listing models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    C = "c"
    RUST = "rust"


class Hal(str, Enum):
    TI = "ti"
    B01LERS = "b01lers"


class Project(BaseModel):
    """A firmware project on disk under ~/emfi-projects/<id>/."""

    id: str = Field(..., description="Filesystem-safe project ID")
    name: str
    language: Language
    target: str = Field("mspm0l2228", description="Target MCU part number")
    hal: Hal
    created_at: datetime
    description: Optional[str] = None
    versions: List[str] = Field(default_factory=list, description="Git tags")


class BuildArtifact(BaseModel):
    """Deterministic build output. Hash covers source tree + toolchain version."""

    project_id: str
    version: Optional[str] = Field(None, description="Git tag or branch")
    sha: str = Field(..., description="Build content hash")
    built_at: datetime
    elf_path: str
    bin_path: str
    listing_path: str
    symbols_path: str
    success: bool
    log_tail: Optional[str] = None


class AssemblyInstruction(BaseModel):
    """One disassembled instruction with source mapping."""

    pc: int = Field(..., description="Program counter (hex address)")
    bytes_hex: str = Field(..., description="Machine code bytes, hex string")
    mnemonic: str
    operands: str = ""
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    function: Optional[str] = None


class AssemblyListing(BaseModel):
    """Result of `arm-none-eabi-objdump -d` parsed into structured form."""

    project_id: str
    build_sha: str
    cpu_mhz: float = Field(32.0, description="Used by View to convert cycles to delay_us")
    instructions: List[AssemblyInstruction]


class GlitchTarget(BaseModel):
    """User-annotated target instruction. Stored in `targets.json` per project."""

    pc_address: int
    name: str
    expected_delay_cycles: Optional[int] = Field(
        None,
        description="Cycles from a known reference point (e.g. trigger rising edge)",
    )
    notes: Optional[str] = None
    created_at: datetime
