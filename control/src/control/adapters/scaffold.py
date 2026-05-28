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

        if mode in ("disabled", "software"):
            pass
        elif mode == "one-shot":
            # donjon-scaffold 0.9.x Chain: events[i] are input signals (rising
            # edges advance the chain), trigger is the output signal.
            # (Earlier versions of this adapter wrongly called chain0.signal(...);
            #  Chain only exposes .events / .trigger / .rearm.)
            try:
                self._impl.sig_connect(self._impl.d0, self._impl.chain0.events[0])
                self._impl.sig_connect(self._impl.chain0.trigger, self._impl.a0)
            except Exception as exc:
                LOGGER.warning(
                    "one-shot wiring failed (%s); falling back to software trigger. "
                    "TODO: confirm donjon-scaffold chain API on this firmware.",
                    exc,
                )
                mode = "software"
        elif mode == "free-run":
            try:
                self._impl.sig_connect(self._impl.pgen0.out, self._impl.a0)
            except Exception as exc:
                LOGGER.warning(
                    "free-run wiring failed (%s); falling back to software trigger.",
                    exc,
                )
                mode = "software"

        self.trigger_mode = mode
        LOGGER.debug("Scaffold trigger mode set to %s", mode)

    def arm_attempt(self) -> None:
        """Prepare for the next verdict (reset pin-edge latches)."""
        self._require_connected()
        if self.trigger_mode == "one-shot":
            try:
                self._impl.chain0.rearm()
            except Exception as exc:
                LOGGER.debug("chain0.rearm failed: %s", exc)
        for pin_name in ("d1", "d2", "d3"):
            pin = getattr(self._impl, pin_name, None)
            if pin is not None and hasattr(pin, "clear_event"):
                try:
                    pin.clear_event()
                except Exception as exc:
                    LOGGER.debug("%s.clear_event failed: %s", pin_name, exc)

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

    # ------------------------------------------------------------------
    # Pin I/O surface used by per-project host/run.py scripts.
    #
    # donjon-scaffold 0.9.5 IO model (introspected — docstring lies about
    # the setter):
    #   IO.value         -> READ-ONLY property; getter senses external input
    #   pin << 0 or 1    -> Signal.__lshift__ → sc.sig_connect(pin, value)
    #                        routes a constant signal to drive the pin;
    #                        equivalent to sc.sig_connect(pin, value)
    #   pin.reg_value    -> the underlying Register (bit 0 = value,
    #                        bit 1 = event); writable but bypasses the
    #                        signal-routing matrix
    #
    # Direction is implicit: a pin with no signal driving it is an input
    # (high-Z, .value getter senses external); a pin with sig_connect(pin, N)
    # is an output driven to N. There is no per-pin disconnect; the
    # nuclear option is sc.sig_disconnect_all() which is too broad.
    # ``set_d_input`` is therefore a no-op declaration in this lib version.
    # ------------------------------------------------------------------

    def _get_pin(self, idx: int) -> Any:
        pin = getattr(self._impl, f"d{idx}", None)
        if pin is None:
            raise ValueError(f"Scaffold has no pin d{idx}")
        return pin

    def set_d_output(self, idx: int) -> None:
        """Claim d<idx> as a push-pull output, driving low initially."""
        self._require_connected()
        self._impl.sig_connect(self._get_pin(idx), 0)

    def set_d_input(self, idx: int) -> None:
        """Declare d<idx> as an input.

        No-op on donjon-scaffold 0.9.5: a pin with no peripheral connected
        is already an input. Kept for symmetry with set_d_output and the
        existing host-script template.
        """
        self._require_connected()

    def write_d(self, idx: int, value: int) -> None:
        """Drive d<idx> low (0) or high (1)."""
        self._require_connected()
        self._impl.sig_connect(self._get_pin(idx), 1 if value else 0)

    def read_d(self, idx: int) -> int:
        """Sense the current logic level on d<idx>."""
        self._require_connected()
        return int(self._get_pin(idx).value)

    # ---- per-pin aliases matching the existing host-script template ----
    # (Newer templates should prefer set_d_output(idx) etc.)

    def set_d0_output(self) -> None:
        self.set_d_output(0)

    def set_d1_input(self) -> None:
        self.set_d_input(1)

    def set_d2_input(self) -> None:
        self.set_d_input(2)

    def set_d3_input(self) -> None:
        self.set_d_input(3)

    def set_d0(self, value: int) -> None:
        self.write_d(0, value)

    def read_d1(self) -> int:
        return self.read_d(1)

    def read_d2(self) -> int:
        return self.read_d(2)

    def read_d3(self) -> int:
        return self.read_d(3)

    @property
    def raw(self) -> Any:
        """Underlying ``donjon-scaffold`` Scaffold instance. Use sparingly."""
        self._require_connected()
        return self._impl
