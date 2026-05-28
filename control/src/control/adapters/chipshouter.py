"""ChipSHOUTER (EMFI pulse source) adapter.

Wraps the ``chipshouter`` pip package. The library exposes most controls
as properties with getters/setters on a ``ChipSHOUTER(comport)`` instance.

Critical invariants (from old-em-setup/HANDOFF.md):
- ``arm()`` MUST be idempotent. The upstream ``armed = True`` calls
  ``cmd_arm()`` which raises ``Firmware_State_Exception`` if already armed.
- ``arm()`` MUST have a timeout. ``wait_for_arm()`` blocks indefinitely
  if HV doesn't come up.
- ``disarm_safe()`` must never raise.

Library API surface (confirmed by probe):
    ChipSHOUTER(comport)
    .state (property, read-only) -> str
    .voltage (property, settable) -> int
    .pulse (property, settable) -> triggers pulse when set to True
    .armed (property, settable) -> calls cmd_arm/cmd_disarm
    .mute (property, settable) -> bool
    .arm_timeout (property, settable) -> int (minutes)
    .faults_current (property, settable)
    .faults_latched (property, read-only)
    .hwtrig_mode (property, settable)
    .hwtrig_term (property, settable)
    .wait_for_arm(timeout=3) -> blocks until armed
    .disconnect()
    .clr_armed (property) -> clears faults then arms
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, List, Optional

from control.adapters.base import BaseAdapter

try:
    from chipshouter.com_tools import Reset_Exception  # type: ignore[import-not-found]
except ImportError:  # library not installed in this env
    class Reset_Exception(Exception):  # type: ignore[no-redef]
        """Stand-in for chipshouter.com_tools.Reset_Exception when the lib
        is not installed (e.g. in test environments)."""

LOGGER = logging.getLogger(__name__)

# Time to wait after a Reset_Exception before retrying. Per the lib's own
# documented behavior: "wait 5 seconds then reinitialize."
_RESET_RECOVERY_SLEEP = 5.0
_RESET_RETRY_LIMIT = 2  # one initial try + one retry


class ChipShouterAdapter(BaseAdapter):
    name = "chipshouter"

    def __init__(self) -> None:
        self._impl = None
        self._port: Optional[str] = None
        self._last_error: Optional[str] = None

    def connect(self, port: Optional[str] = None) -> None:
        if port is None:
            raise ValueError("chipshouter: no serial port specified")
        try:
            from chipshouter import ChipSHOUTER
        except ImportError as exc:
            self._last_error = f"chipshouter library not installed: {exc}"
            raise RuntimeError(self._last_error) from exc

        LOGGER.info("ChipSHOUTER connecting on %s", port)
        self._impl = ChipSHOUTER(port)
        self._port = port
        self._last_error = None
        state = str(self._impl.state)
        LOGGER.info("ChipSHOUTER connected — state: %s, voltage: %s",
                     state, self._impl.voltage)

    def disconnect(self) -> None:
        if self._impl is not None:
            LOGGER.info("ChipSHOUTER disconnecting")
            try:
                self._impl.disconnect()
            except Exception as exc:
                LOGGER.warning("ChipSHOUTER disconnect error: %s", exc)
            self._impl = None
            self._port = None

    @property
    def connected(self) -> bool:
        return self._impl is not None

    def _require_connected(self) -> None:
        if self._impl is None:
            raise RuntimeError("ChipSHOUTER is not connected")

    def _with_reset_retry(self, label: str, fn: Callable[[], Any]) -> Any:
        """Run ``fn`` with one retry on ``Reset_Exception``.

        The ChipSHOUTER occasionally resets during property writes and
        verification reads (well-known recurring condition; the lib's own
        docstring recommends sleeping 5s then retrying). If a Reset_Exception
        still fires on the retry, raise RuntimeError with the recovery
        steps the user should take.
        """
        for attempt in range(_RESET_RETRY_LIMIT):
            try:
                return fn()
            except Reset_Exception:
                LOGGER.warning(
                    "ChipSHOUTER reset during %s (attempt %d); waiting %.0fs for reinit",
                    label, attempt + 1, _RESET_RECOVERY_SLEEP,
                )
                time.sleep(_RESET_RECOVERY_SLEEP)
        raise RuntimeError(
            f"ChipSHOUTER reset {_RESET_RETRY_LIMIT} times during {label}; "
            "check HV/USB and retry. If this persists, the chipshouter "
            "Python instance may need to be re-created (disconnect/reconnect)."
        )

    def configure(
        self,
        voltage: int,
        pulse_width_ns: int,
        pulse_repeat: int = 1,
        pulse_deadtime_ms: int = 10,
        arm_timeout_min: int = 1,
        mute: bool = True,
    ) -> None:
        self._require_connected()

        def _do_configure() -> None:
            self._impl.voltage = voltage
            self._impl.pulse.repeat = pulse_repeat
            self._impl.pulse.width = pulse_width_ns
            self._impl.pulse.deadtime = pulse_deadtime_ms * 1000
            self._impl.arm_timeout = arm_timeout_min
            self._impl.mute = mute

        self._with_reset_retry("configure", _do_configure)
        LOGGER.info("ChipSHOUTER configured: V=%d width=%dns repeat=%d mute=%s",
                     voltage, pulse_width_ns, pulse_repeat, mute)

    def arm(self, clear_faults: bool = False, timeout_s: float = 5.0) -> None:
        """Idempotent arm with timeout. No-op if already armed.

        Reset_Exception can surface in the lib at any of the property reads
        and writes below; wrap the whole body in the retry helper.
        """
        self._require_connected()

        def _do_arm() -> bool:
            """Return True if armed (either already or after our request)."""
            state = str(self._impl.state).lower()
            if "fault" in state:
                LOGGER.warning("ChipSHOUTER in fault state (%s), clearing", state)
                self._impl.faults_current = 0
                time.sleep(0.1)
                state = str(self._impl.state).lower()
            if "armed" in state:
                LOGGER.debug("ChipSHOUTER already armed, skipping")
                return True
            LOGGER.info("ChipSHOUTER arming (timeout=%.1fs)", timeout_s)
            self._impl.armed = True
            return False

        already_armed = self._with_reset_retry("arm", _do_arm)
        if already_armed:
            return

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                s = str(self._impl.state).lower()
            except Reset_Exception:
                LOGGER.warning(
                    "ChipSHOUTER reset during arm wait; waiting %.0fs for reinit",
                    _RESET_RECOVERY_SLEEP,
                )
                time.sleep(_RESET_RECOVERY_SLEEP)
                continue
            if "armed" in s:
                LOGGER.info("ChipSHOUTER armed")
                return
            time.sleep(0.1)

        raise RuntimeError(
            f"ChipSHOUTER failed to arm within {timeout_s}s "
            f"(state: {self._impl.state})"
        )

    def disarm(self) -> None:
        self._require_connected()
        LOGGER.info("ChipSHOUTER disarming")
        self._impl.armed = False

    def disarm_safe(self) -> None:
        """Best-effort disarm — never raises."""
        if self._impl is None:
            return
        try:
            state = str(self._impl.state).lower()
            if "armed" not in state:
                return
            self._impl.armed = False
            LOGGER.info("ChipSHOUTER disarmed (safe)")
        except Exception as exc:
            LOGGER.warning("disarm_safe swallowed: %s", exc)

    def pulse(self) -> None:
        self._require_connected()
        self._impl.pulse = True

    def get_state(self) -> str:
        self._require_connected()
        return str(self._impl.state)

    def get_fault_active(self) -> List[Any]:
        self._require_connected()
        faults = self._impl.faults_current
        if faults:
            return [str(faults)]
        return []
