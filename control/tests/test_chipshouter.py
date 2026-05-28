"""ChipShouterAdapter tests — verifies Reset_Exception retry behavior.

The ChipSHOUTER occasionally resets during property writes; the lib raises
``chipshouter.com_tools.Reset_Exception``. The adapter retries once after
a 5s sleep before giving up.
"""

from __future__ import annotations

from typing import Any, List
from unittest.mock import patch

import pytest

from control.adapters.chipshouter import ChipShouterAdapter, Reset_Exception


class _FakePulse:
    def __init__(self) -> None:
        self.repeat = 1
        self.width = 0
        self.deadtime = 0


class _FakeImpl:
    """Configurable chipshouter stand-in.

    ``reset_on`` is a list of property-name strings; assigning to those
    properties raises Reset_Exception the first time, then succeeds.
    ``state_sequence`` is a list of state strings returned by .state in order.
    """

    def __init__(
        self,
        reset_on_voltage_writes: int = 0,
        state_sequence: List[str] = ("ready", "armed"),
    ) -> None:
        # Bypass __setattr__ for initialization so the voltage default
        # doesn't trip the injected Reset_Exception.
        for k, v in {
            "_reset_remaining": reset_on_voltage_writes,
            "_state_sequence": list(state_sequence),
            "_state_idx": 0,
            "voltage": 0,
            "pulse": _FakePulse(),
            "arm_timeout": 0,
            "mute": False,
            "armed": False,
            "faults_current": 0,
            "faults_latched": None,
        }.items():
            object.__setattr__(self, k, v)

    def __setattr__(self, name: str, value: Any) -> None:
        # Inject Reset_Exception during voltage writes if requested.
        if name == "voltage" and self._reset_remaining > 0:
            object.__setattr__(self, "_reset_remaining", self._reset_remaining - 1)
            raise Reset_Exception("simulated reset")
        object.__setattr__(self, name, value)

    @property
    def state(self) -> str:
        if self._state_idx < len(self._state_sequence):
            s = self._state_sequence[self._state_idx]
            self._state_idx += 1
            return s
        return self._state_sequence[-1]


def test_configure_retries_after_reset_exception():
    """First write raises Reset_Exception; retry succeeds."""
    sa = ChipShouterAdapter()
    sa._impl = _FakeImpl(reset_on_voltage_writes=1)
    with patch("control.adapters.chipshouter.time.sleep") as sleep_mock:
        sa.configure(voltage=500, pulse_width_ns=80)
    # voltage write attempted twice (first raised, second succeeded)
    assert sa._impl.voltage == 500
    # 5-second recovery sleep occurred at least once
    sleep_calls = [c.args[0] for c in sleep_mock.call_args_list]
    assert 5.0 in sleep_calls


def test_configure_gives_up_after_two_resets():
    """Both writes raise Reset_Exception → RuntimeError with hint."""
    sa = ChipShouterAdapter()
    sa._impl = _FakeImpl(reset_on_voltage_writes=999)
    with patch("control.adapters.chipshouter.time.sleep"):
        with pytest.raises(RuntimeError, match="reset.*times.*configure"):
            sa.configure(voltage=500, pulse_width_ns=80)


def test_configure_succeeds_clean_path():
    sa = ChipShouterAdapter()
    sa._impl = _FakeImpl(reset_on_voltage_writes=0)
    sa.configure(voltage=300, pulse_width_ns=100, mute=True)
    assert sa._impl.voltage == 300
    assert sa._impl.pulse.width == 100
    assert sa._impl.mute is True


def test_arm_idempotent_when_already_armed():
    """If state reads as 'armed' already, no cmd_arm is sent."""
    sa = ChipShouterAdapter()
    sa._impl = _FakeImpl(state_sequence=["armed"])
    sa.arm(timeout_s=1.0)
    # We never set armed=True because we shortcut.
    assert sa._impl.armed is False


def test_arm_succeeds_when_state_transitions():
    sa = ChipShouterAdapter()
    sa._impl = _FakeImpl(state_sequence=["ready", "armed"])
    sa.arm(timeout_s=1.0)
    assert sa._impl.armed is True
