"""Ledger Donjon Scaffold board adapter.

Wraps the `donjon-scaffold` pip package. Handles:
- DUT power + recovery (cycle Vcc on hang)
- D0/D1/D2/D3 pin map to target's USER_TEST, USER_HEARTBEAT, USER_LED_2,
  USER_LED_3 respectively (see old-em-setup/HANDOFF.md wiring diagram).
- A0 external trigger to ChipSHOUTER, with three modes:
    * disabled
    * software   (trigger via USB; ChipShouter.pulse())
    * one-shot   (Scaffold chain module fires A0 on rising D0)
    * free-run   (A0 always connected to Scaffold pgen output)
- arm_attempt() — preps for next verdict read
- wait_verdict(timeout_s) — polls D1/D2/D3 until verdict or timeout
- dut_power_cycle()

TODO: use the public close() API rather than poking
`self.bus.ser.close()` like the old code did (HANDOFF "Scaffold close fragile").
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from control.adapters.base import BaseAdapter

LOGGER = logging.getLogger(__name__)


class ScaffoldAdapter(BaseAdapter):
    name = "scaffold"
    trigger_mode: str = "software"  # disabled | software | one-shot | free-run

    def __init__(self) -> None:
        self._impl = None

    def connect(self, port: Optional[str] = None) -> None:
        raise NotImplementedError("ScaffoldAdapter.connect")

    def disconnect(self) -> None:
        raise NotImplementedError("ScaffoldAdapter.disconnect")

    @property
    def connected(self) -> bool:
        return self._impl is not None

    def set_trigger_mode(self, mode: str) -> None:
        raise NotImplementedError("ScaffoldAdapter.set_trigger_mode")

    def arm_attempt(self) -> None:
        """Prepare for the next verdict (reset pin-edge latches)."""
        raise NotImplementedError("ScaffoldAdapter.arm_attempt")

    def wait_verdict(self, timeout_s: float) -> Dict[str, Any]:
        """Poll D1/D2/D3 until verdict or timeout. Returns:
        { fault: bool, heartbeat_alive: bool, campaign_complete: bool }
        """
        raise NotImplementedError("ScaffoldAdapter.wait_verdict")

    def dut_power_cycle(self) -> None:
        raise NotImplementedError("ScaffoldAdapter.dut_power_cycle")
