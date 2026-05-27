"""XDS110 programmer / debugger adapter.

Two backends, both subprocess-based:

1. **TI dslite / UniFlash CLI** — fast, headless flashing. Used by
   `flash()` for the build → flash → campaign loop. Path configured via
   `config.programmer.dslite_bin` or env `DSLITE_BIN`.

2. **OpenOCD** — interactive debugging. Used by `attach_debugger()` to
   spin up an OpenOCD daemon on configurable gdb/telnet ports for
   combined SW + HW attack analysis. Path via `config.programmer.openocd_bin`
   or env `OPENOCD_BIN`. Requires an OpenOCD config for MSPM0L2228 +
   XDS110 (typically `interface/xds110.cfg` + custom MSPM0 target).

Neither backend uses pyserial — both are subprocess wrappers, so they
do NOT need to live behind a DeviceWorker; instead, isolate per-process
state on the adapter instance and serialize at the router layer.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from control.adapters.base import BaseAdapter

LOGGER = logging.getLogger(__name__)


class XDS110Adapter(BaseAdapter):
    name = "xds110"

    def __init__(
        self,
        dslite_bin: Optional[str] = None,
        openocd_bin: Optional[str] = None,
        openocd_config: Optional[str] = None,
    ) -> None:
        self.dslite_bin = dslite_bin
        self.openocd_bin = openocd_bin
        self.openocd_config = openocd_config
        self._debug_proc: Optional[subprocess.Popen] = None

    def connect(self, port: Optional[str] = None) -> None:
        """No-op for subprocess-based adapter; presence-detect via XDS110 USB instead."""
        pass

    def disconnect(self) -> None:
        self.detach_debugger()

    @property
    def connected(self) -> bool:
        # TODO: actually probe XDS110 presence via lsusb / dslite --probe
        return False

    def flash(self, elf_path: Path) -> dict:
        """Flash via dslite. Returns {success, log_tail}."""
        raise NotImplementedError("XDS110Adapter.flash (dslite subprocess)")

    def reset(self) -> None:
        raise NotImplementedError("XDS110Adapter.reset")

    def attach_debugger(self, gdb_port: int = 3333, telnet_port: int = 4444) -> dict:
        """Spawn `openocd -f <cfg>` in the background."""
        raise NotImplementedError("XDS110Adapter.attach_debugger (openocd subprocess)")

    def detach_debugger(self) -> None:
        if self._debug_proc is not None:
            LOGGER.info("Terminating OpenOCD process (pid=%d)", self._debug_proc.pid)
            try:
                self._debug_proc.terminate()
                self._debug_proc.wait(timeout=5)
            except Exception:
                LOGGER.warning("OpenOCD process did not terminate cleanly")
            self._debug_proc = None
