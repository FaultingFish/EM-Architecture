"""ChipShover (XY positioning table) adapter.

Wraps the `chipshover` pip package. Reference shape: the old
EMFI_Interfacing/ submodule ChipShoverAdapter.

Build-out tasks:
- Open serial via pyserial under control.workers.DeviceWorker
- move_absolute_logical(x, y, z) — applies origin offset + axis inversion
- move_absolute_machine(x, y, z) — raw coords
- get_position()
- home(), set_origin()
- Translate units consistently (mm)
"""

from __future__ import annotations

from typing import Optional

from control.adapters.base import BaseAdapter


class ChipShoverAdapter(BaseAdapter):
    name = "chipshover"

    def __init__(self) -> None:
        self._impl = None
        self._port: Optional[str] = None

    def connect(self, port: Optional[str] = None) -> None:
        raise NotImplementedError("ChipShoverAdapter.connect")

    def disconnect(self) -> None:
        raise NotImplementedError("ChipShoverAdapter.disconnect")

    @property
    def connected(self) -> bool:
        return self._impl is not None

    def move_absolute_logical(self, x: float, y: float, z: float) -> None:
        raise NotImplementedError("ChipShoverAdapter.move_absolute_logical")

    def get_position(self) -> tuple[float, float, float]:
        raise NotImplementedError("ChipShoverAdapter.get_position")
