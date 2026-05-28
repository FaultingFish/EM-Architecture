"""ScaffoldAdapter tests.

The non-hardware test uses a fake ``_impl`` to verify the adapter dispatches
through ``sig_connect`` for writes (donjon-scaffold 0.9.5 has no
``IO.value`` setter, so the previous ``pin.value = N`` form was silently
broken at runtime).

The ``@pytest.mark.hw`` test exercises the real Scaffold board.
"""

from __future__ import annotations

from typing import Any, List, Tuple

import pytest

from control.adapters.scaffold import ScaffoldAdapter


class _FakePin:
    """Minimal IO stand-in. Records what gets written."""

    def __init__(self) -> None:
        self.value = 0  # getter-only on real IO; on the fake we use plain attr


class _FakeImpl:
    """Just enough donjon-scaffold surface for the adapter's pin methods."""

    def __init__(self) -> None:
        self.d0 = _FakePin()
        self.d1 = _FakePin()
        self.d2 = _FakePin()
        self.d3 = _FakePin()
        self.sig_connect_calls: List[Tuple[Any, Any]] = []

    def sig_connect(self, a: Any, b: Any) -> None:
        self.sig_connect_calls.append((a, b))


def test_set_d_output_routes_constant_zero_via_sig_connect():
    sa = ScaffoldAdapter()
    sa._impl = _FakeImpl()
    sa.set_d_output(0)
    assert sa._impl.sig_connect_calls == [(sa._impl.d0, 0)]


def test_write_d_routes_constant_via_sig_connect():
    sa = ScaffoldAdapter()
    sa._impl = _FakeImpl()
    sa.write_d(0, 1)
    sa.write_d(0, 0)
    assert sa._impl.sig_connect_calls == [
        (sa._impl.d0, 1),
        (sa._impl.d0, 0),
    ]


def test_write_d_does_not_assign_value():
    """Regression: previously did `pin.value = N` which raises on real IO."""
    sa = ScaffoldAdapter()
    impl = _FakeImpl()

    class _ReadOnlyPin:
        @property
        def value(self) -> int:
            return 0
        # no setter — assigning .value would raise AttributeError

    impl.d0 = _ReadOnlyPin()
    sa._impl = impl
    # Must not raise: the write path goes via sig_connect, not .value =.
    sa.write_d(0, 1)
    assert impl.sig_connect_calls == [(impl.d0, 1)]


def test_read_d_uses_value_getter():
    sa = ScaffoldAdapter()
    impl = _FakeImpl()
    impl.d1.value = 1
    sa._impl = impl
    assert sa.read_d(1) == 1


def test_set_d_input_is_no_op_in_lib_0_9_5():
    sa = ScaffoldAdapter()
    sa._impl = _FakeImpl()
    sa.set_d_input(1)
    # No signal-routing call: input is the default state.
    assert sa._impl.sig_connect_calls == []


def test_aliases_dispatch_to_generic_methods():
    sa = ScaffoldAdapter()
    sa._impl = _FakeImpl()
    sa.set_d0_output()
    sa.set_d0(1)
    sa.set_d1_input()
    sa._impl.d1.value = 1
    sa._impl.d2.value = 0
    sa._impl.d3.value = 1
    assert sa.read_d1() == 1
    assert sa.read_d2() == 0
    assert sa.read_d3() == 1
    # set_d0_output drives 0, set_d0(1) drives 1
    assert sa._impl.sig_connect_calls == [
        (sa._impl.d0, 0),
        (sa._impl.d0, 1),
    ]


def test_unknown_pin_raises():
    sa = ScaffoldAdapter()
    sa._impl = _FakeImpl()
    with pytest.raises(ValueError, match="d99"):
        sa.set_d_output(99)


@pytest.mark.hw
def test_scaffold_pin_io_roundtrip():
    """Hardware: open the real board, drive D0, read D1.

    Marked hw so it's skipped in normal runs. Run with ``pytest -m hw``
    on the lab box; expects /dev/ttyUSB0 to be the Scaffold.
    """
    sa = ScaffoldAdapter()
    sa.connect("/dev/ttyUSB0")
    try:
        sa.set_d_output(0)
        sa.write_d(0, 1)
        sa.write_d(0, 0)
        # If D0 is looped to D1 in hardware, this should read what we wrote.
        # Otherwise the call still must not raise.
        _ = sa.read_d(1)
    finally:
        sa.disconnect()
