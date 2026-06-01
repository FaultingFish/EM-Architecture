from __future__ import annotations

from control.adapters.xds110 import XDS110Adapter


def test_xds110_connect_tracks_detected_port():
    adapter = XDS110Adapter()

    assert adapter.connected is False

    adapter.connect("/dev/serial/by-id/xds110")

    assert adapter.connected is True
    assert adapter._port == "/dev/serial/by-id/xds110"


def test_xds110_disconnect_clears_status():
    adapter = XDS110Adapter()
    adapter.connect("/dev/serial/by-id/xds110")

    adapter.disconnect()

    assert adapter.connected is False
    assert adapter._port is None
