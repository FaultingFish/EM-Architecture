"""Campaign engine: per-attempt sequencing + multi-dimensional sweep.

Carry-forward of old-em-setup/glitchweb/backend/app/orchestrator.py's
perform_attempt() + run_scan(). Extended to sweep delay × pulse_width ×
voltage on top of the XYZ grid, and to support replay(run_id).

The build-out session that fills this in should:
1. Lift `perform_attempt` from the old file verbatim, replacing direct
   device imports with the new control.adapters.*.
2. Replace the triple-nested XYZ loop with an iterator over
   (xyz_grid × sweep_dimensions), still serpentine on Y.
3. Add `replay(run_id)`: fetch the AttemptResult from logbook,
   jog to its position, re-fire its pulse parameters.

Reference: old orchestrator at
old-em-setup/glitchweb/backend/app/orchestrator.py
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from control.logbook import Logbook
from control.safety import ArmGate, RateLimiter, StopFlag
from control.state import AppState

LOGGER = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        state: AppState,
        arm_gate: ArmGate,
        stop_flag: StopFlag,
        rate_limiter: RateLimiter,
        logbook: Logbook,
        shover: Any,        # adapters.chipshover.ChipShoverAdapter
        shouter: Any,       # adapters.chipshouter.ChipShouterAdapter
        scaffold: Any,      # adapters.scaffold.ScaffoldAdapter
        broadcast: Callable[[Dict[str, Any]], None],
    ):
        self.state = state
        self.arm_gate = arm_gate
        self.stop_flag = stop_flag
        self.rate_limiter = rate_limiter
        self.logbook = logbook
        self.shover = shover
        self.shouter = shouter
        self.scaffold = scaffold
        self.broadcast = broadcast
        self._task: Optional[asyncio.Task] = None
        self._task_lock = asyncio.Lock()

    async def perform_attempt(
        self,
        verdict_timeout_s: float,
        pulse_params: Dict[str, Any],
        shouter_auto_arm: bool = True,
    ) -> Dict[str, Any]:
        """Single glitch attempt at the current position.

        TODO: lift implementation from old orchestrator perform_attempt().
        Lines 49-137 in old-em-setup/glitchweb/backend/app/orchestrator.py.
        """
        raise NotImplementedError(
            "perform_attempt: port from old-em-setup/glitchweb/backend/app/orchestrator.py:49"
        )

    async def run_campaign(
        self,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a full campaign.

        Sweep dimensions (in nesting order, outermost first):
          z → y → x (serpentine) → delay_us → pulse_width_ns → voltage_v
            → attempts_per_point

        TODO: lift run_scan from old orchestrator, extend with sweep dims.
        Lines 141-222 in old-em-setup/glitchweb/backend/app/orchestrator.py.
        """
        raise NotImplementedError(
            "run_campaign: extend from old-em-setup orchestrator.run_scan"
        )

    async def replay(self, run_id: str) -> Dict[str, Any]:
        """Re-execute the attempt identified by run_id.

        Fetch the AttemptResult from the logbook, jog to its (x, y, z),
        and fire the same pulse parameters.
        """
        raise NotImplementedError("replay")
