"""ChipShover (XY positioning table) adapter.

Wraps the ``chipshover`` pip package (install from GitHub, not PyPI —
the PyPI tarball is malformed). The library speaks G-code over serial
to either Smoothieware or Marlin firmware.

Library API surface (confirmed by probe):
    ChipShover(comport)
    .get_position(forcefinish=True) -> (x, y, z)
    .move(x=None, y=None, z=None)  # absolute, blocks via M400
    .home(x=True, y=True, z=True)  # G28, blocks
    .close()

Logical↔machine coordinate translation lives here (ported from
old-em-setup/glitchweb/backend/app/devices/chipshover_dev.py:92-104).
``set_origin()`` records the current machine position as the logical
origin; all logical moves add that offset.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from control.adapters.base import BaseAdapter

LOGGER = logging.getLogger(__name__)


class ChipShoverAdapter(BaseAdapter):
    name = "chipshover"

    def __init__(self) -> None:
        self._impl = None
        self._port: Optional[str] = None
        self._last_error: Optional[str] = None
        self._origin_machine: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._origin_set: bool = False

    def connect(self, port: Optional[str] = None) -> None:
        if port is None:
            raise ValueError("chipshover: no serial port specified")
        try:
            from chipshover import ChipShover
        except ImportError as exc:
            self._last_error = f"chipshover library not installed: {exc}"
            raise RuntimeError(self._last_error) from exc

        LOGGER.info("ChipShover connecting on %s", port)
        self._impl = ChipShover(port)
        self._port = port
        self._last_error = None
        pos = self._impl.get_position()
        LOGGER.info("ChipShover connected — position: %s", pos)

    def disconnect(self) -> None:
        if self._impl is not None:
            LOGGER.info("ChipShover disconnecting")
            try:
                self._impl.close()
            except Exception as exc:
                LOGGER.warning("ChipShover close error: %s", exc)
            self._impl = None
            self._port = None

    @property
    def connected(self) -> bool:
        return self._impl is not None

    def _require_connected(self) -> None:
        if self._impl is None:
            raise RuntimeError("ChipShover is not connected")

    def get_position(self) -> Tuple[float, float, float]:
        self._require_connected()
        x, y, z = self._impl.get_position()
        return (float(x), float(y), float(z))

    def get_position_logical(self) -> Tuple[float, float, float]:
        mx, my, mz = self.get_position()
        return self._machine_to_logical(mx, my, mz)

    def move_absolute_logical(self, x: float, y: float, z: float) -> None:
        self._require_connected()
        mx, my, mz = self._logical_to_machine(x, y, z)
        LOGGER.debug("move_absolute_logical(%s, %s, %s) -> machine(%s, %s, %s)",
                      x, y, z, mx, my, mz)
        self._impl.move(x=mx, y=my, z=mz)

    def move_relative(self, axis: str, distance: float) -> None:
        self._require_connected()
        cx, cy, cz = self.get_position()
        axis_upper = axis.upper()
        if axis_upper == "X":
            cx += distance
        elif axis_upper == "Y":
            cy += distance
        elif axis_upper == "Z":
            cz += distance
        else:
            raise ValueError(f"Invalid axis: {axis}")
        LOGGER.debug("move_relative(%s, %s) -> machine(%s, %s, %s)",
                      axis, distance, cx, cy, cz)
        self._impl.move(x=cx, y=cy, z=cz)

    def home(self) -> None:
        self._require_connected()
        LOGGER.info("ChipShover homing")
        self._impl.home()
        self._origin_set = False
        self._origin_machine = (0.0, 0.0, 0.0)
        LOGGER.info("ChipShover homed — origin cleared")

    def set_origin(self) -> None:
        self._require_connected()
        pos = self.get_position()
        self._origin_machine = pos
        self._origin_set = True
        LOGGER.info("ChipShover origin set at machine %s", pos)

    def _logical_to_machine(
        self, x: float, y: float, z: float
    ) -> Tuple[float, float, float]:
        ox, oy, oz = self._origin_machine
        return (ox + x, oy + y, oz + z)

    def _machine_to_logical(
        self, mx: float, my: float, mz: float
    ) -> Tuple[float, float, float]:
        ox, oy, oz = self._origin_machine
        return (mx - ox, my - oy, mz - oz)
