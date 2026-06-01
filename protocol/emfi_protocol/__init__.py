"""Shared Pydantic models for the EMFI research platform.

These types are the single source of truth for the wire format between
Control, Develop, and View. Both Python apps import from here; the
SvelteKit apps consume the OpenAPI specs generated from FastAPI routes
that reference these models.
"""

from emfi_protocol.campaigns import Campaign, GridParams, StopConditions, SweepParams
from emfi_protocol.devices import ArmState, DeviceStatus, Position
from emfi_protocol.projects import (
    AssemblyInstruction,
    AssemblyListing,
    BuildArtifact,
    FlashedFirmware,
    GlitchTarget,
    Project,
)
from emfi_protocol.runs import AttemptResult, Outcome, Verdict
from emfi_protocol.ws_events import WsEvent, WsTopic

__all__ = [
    "Campaign",
    "GridParams",
    "StopConditions",
    "SweepParams",
    "ArmState",
    "DeviceStatus",
    "Position",
    "AssemblyInstruction",
    "AssemblyListing",
    "BuildArtifact",
    "FlashedFirmware",
    "GlitchTarget",
    "Project",
    "AttemptResult",
    "Outcome",
    "Verdict",
    "WsEvent",
    "WsTopic",
]
