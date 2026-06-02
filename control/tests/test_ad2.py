from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pytest

from control.adapters.ad2 import AD2Adapter
from control.routers import devices


def test_ad2_status_is_safe_without_waveforms(monkeypatch):
    monkeypatch.setattr("ctypes.util.find_library", lambda name: None)
    monkeypatch.setattr("ctypes.cdll.LoadLibrary", lambda name: (_ for _ in ()).throw(OSError("missing libdwf")))
    adapter = AD2Adapter()

    status = adapter.status()

    assert status["name"] == "ad2"
    assert status["connected"] is False
    assert status["available"] is False
    assert "mapping" in status


class _FakeAD2:
    connected = False

    def status(self) -> Dict[str, Any]:
        return {"name": "ad2", "available": True, "connected": self.connected}

    def capture(self) -> Dict[str, Any]:
        self.connected = True
        return {
            "name": "ad2",
            "available": True,
            "connected": True,
            "sample_rate_hz": 1_000_000,
            "samples": 2,
            "channels": {
                "pulse": {"values": [0.0, 1.0]},
                "trigger": {"values": [0, 1]},
                "clock": {"values": [1, 0]},
            },
        }


@dataclass
class _FakeContext:
    ad2: _FakeAD2
    broadcasts: List[Tuple[str, Dict[str, Any]]]

    def broadcast(self, topic: str, payload: Dict[str, Any]) -> None:
        self.broadcasts.append((topic, payload))


async def test_ad2_capture_route_broadcasts_capture():
    ctx = _FakeContext(ad2=_FakeAD2(), broadcasts=[])

    capture = await devices.ad2_capture(ctx)

    assert capture["name"] == "ad2"
    assert ctx.broadcasts == [("ad2_capture", capture)]
