"""ChipSHOUTER (EMFI pulse source) adapter.

Wraps the `chipshouter` pip package.

Critical invariants:
- arm() MUST be idempotent (check state before sending cmd_arm). The
  upstream library raises Firmware_State_Exception if you arm twice;
  this was a bug fixed in the old setup (HANDOFF.md).
- wait_for_arm MUST have a timeout. The upstream library can hang
  forever if HV doesn't come up (HANDOFF "Worker hang").
- disarm_safe() — catch all exceptions and disarm anyway.

Reference: old EMFI_Interfacing/ submodule ChipSHOUTERAdapter, plus
old-em-setup/HANDOFF.md sections on shouter bugs.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from control.adapters.base import BaseAdapter

LOGGER = logging.getLogger(__name__)


class ChipShouterAdapter(BaseAdapter):
    name = "chipshouter"

    def __init__(self) -> None:
        self._impl = None

    def connect(self, port: Optional[str] = None) -> None:
        raise NotImplementedError("ChipShouterAdapter.connect")

    def disconnect(self) -> None:
        raise NotImplementedError("ChipShouterAdapter.disconnect")

    @property
    def connected(self) -> bool:
        return self._impl is not None

    def configure(
        self,
        voltage: int,
        pulse_width_ns: int,
        pulse_repeat: int = 1,
        pulse_deadtime_ms: int = 10,
        arm_timeout_min: int = 1,
        mute: bool = True,
    ) -> None:
        raise NotImplementedError("ChipShouterAdapter.configure")

    def arm(self, clear_faults: bool = False, timeout_s: float = 5.0) -> None:
        """Idempotent. No-op if already armed. Times out if HV stalls."""
        raise NotImplementedError("ChipShouterAdapter.arm")

    def disarm(self) -> None:
        raise NotImplementedError("ChipShouterAdapter.disarm")

    def disarm_safe(self) -> None:
        """Best-effort disarm — never raises."""
        try:
            self.disarm()
        except Exception:
            pass

    def pulse(self) -> None:
        raise NotImplementedError("ChipShouterAdapter.pulse")

    def get_state(self) -> str:
        raise NotImplementedError("ChipShouterAdapter.get_state")

    def get_fault_active(self) -> List[Any]:
        raise NotImplementedError("ChipShouterAdapter.get_fault_active")
