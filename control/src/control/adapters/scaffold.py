"""Ledger Donjon Scaffold board adapter.

Wraps the ``donjon-scaffold`` pip package (>= 0.7 for chain module).
Handles DUT power, D0-D3 pin map, A0 trigger modes, and verdict polling.

Pin map (from old-em-setup/HANDOFF.md):
    PA21 USER_TEST       → D0  (input; rising edge = test loop start)
    PB14 USER_HEARTBEAT  → D1  (input; toggled regularly = alive)
    PB10 USER_LED_2      → D2  (input; rising edge = self-detected fault)
    PB9  USER_LED_3      → D3  (input; falling edge = campaign end)
    --                     A0  (output to ChipSHOUTER external trigger)

Trigger modes:
    disabled  — A0 idle, no automatic trigger
    software  — A0 idle; ChipSHOUTER fires via USB (pulse())
    one-shot  — Scaffold chain module fires A0 once on rising D0
    free-run  — A0 continuously connected to pgen output
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from control.adapters.base import BaseAdapter

LOGGER = logging.getLogger(__name__)

_VALID_TRIGGER_MODES = ("disabled", "software", "one-shot", "free-run")


class ScaffoldAdapter(BaseAdapter):
    name = "scaffold"
    trigger_mode: str = "software"

    def __init__(self) -> None:
        self._impl = None
        self._port: Optional[str] = None
        self._last_error: Optional[str] = None
        self._version: Optional[str] = None

    def connect(self, port: Optional[str] = None) -> None:
        if port is None:
            raise ValueError("scaffold: no serial port specified")
        try:
            from scaffold import Scaffold
        except ImportError as exc:
            self._last_error = f"donjon-scaffold library not installed: {exc}"
            raise RuntimeError(self._last_error) from exc

        LOGGER.info("Scaffold connecting on %s", port)
        self._impl = Scaffold(port)
        self._port = port
        self._version = str(self._impl.version)
        self._last_error = None
        LOGGER.info("Scaffold connected — firmware %s", self._version)

    def disconnect(self) -> None:
        if self._impl is not None:
            LOGGER.info("Scaffold disconnecting")
            try:
                self._impl.sig_disconnect_all()
            except Exception as exc:
                LOGGER.debug("sig_disconnect_all: %s", exc)
            try:
                self._impl.power.dut = 0
            except Exception as exc:
                LOGGER.debug("power off on disconnect: %s", exc)
            self._impl = None
            self._port = None

    @property
    def connected(self) -> bool:
        return self._impl is not None

    def _require_connected(self) -> None:
        if self._impl is None:
            raise RuntimeError("Scaffold is not connected")

    def set_trigger_mode(self, mode: str) -> None:
        if mode not in _VALID_TRIGGER_MODES:
            raise ValueError(f"Invalid trigger mode: {mode}. Must be one of {_VALID_TRIGGER_MODES}")
        self._require_connected()

        self._impl.sig_disconnect_all()

        if mode == "disabled":
            pass
        elif mode == "software":
            pass
        elif mode == "one-shot":
            self._impl.sig_connect(self._impl.d0, self._impl.chain0.signal("trigger"))
            self._impl.sig_connect(self._impl.chain0.signal("out"), self._impl.a0)
        elif mode == "free-run":
            self._impl.sig_connect(self._impl.pgen0.signal("out"), self._impl.a0)

        self.trigger_mode = mode
        LOGGER.info("Scaffold trigger mode set to %s", mode)

    def arm_attempt(self) -> None:
        """Prepare for the next verdict (reset pin-edge latches)."""
        self._require_connected()
        if self.trigger_mode == "one-shot":
            self._impl.chain0.rearm()
        for pin in (self._impl.d1, self._impl.d2, self._impl.d3):
            pin.clear_event()

    def wait_verdict(self, timeout_s: float) -> Dict[str, Any]:
        """Poll D1/D2/D3 until verdict or timeout.

        Returns the shape emfi_protocol.runs.Verdict expects:
            { fault: bool, heartbeat_alive: bool, campaign_complete: bool }
        """
        self._require_connected()
        deadline = time.monotonic() + timeout_s
        fault = False
        heartbeat_alive = False
        campaign_complete = False

        while time.monotonic() < deadline:
            if self._impl.d2.event:
                fault = True
            if self._impl.d1.event:
                heartbeat_alive = True
            if self._impl.d3.event:
                campaign_complete = True
            if fault or heartbeat_alive:
                break
            time.sleep(0.005)

        return {
            "fault": fault,
            "heartbeat_alive": heartbeat_alive,
            "campaign_complete": campaign_complete,
        }

    def dut_power_cycle(self, off_time: float = 0.05) -> None:
        """Power-cycle the DUT via Scaffold's power module."""
        self._require_connected()
        LOGGER.info("DUT power cycle (off_time=%.3fs)", off_time)
        self._impl.power.dut = 0
        time.sleep(off_time)
        self._impl.power.dut = 1
        time.sleep(0.05)

    def dut_power(self, on: bool) -> None:
        self._require_connected()
        self._impl.power.dut = 1 if on else 0
        LOGGER.info("DUT power %s", "ON" if on else "OFF")
