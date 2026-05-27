"""Tests for the campaign engine.

Skeleton only — flesh out once the orchestrator is ported. Use fake
adapters (in-memory state, no hardware) to exercise classification,
sweep math, and stop-flag responsiveness.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="orchestrator not yet ported from old setup")
def test_perform_attempt_classifies_glitch():
    """When verdict.fault is True, outcome should be 'glitch'."""
    raise NotImplementedError


@pytest.mark.skip(reason="orchestrator not yet ported from old setup")
def test_perform_attempt_classifies_hang():
    """When heartbeat_alive is False, outcome should be 'hang'."""
    raise NotImplementedError


@pytest.mark.skip(reason="orchestrator not yet ported from old setup")
def test_run_campaign_serpentine_y():
    """Y axis should alternate direction between Z planes to avoid backlash."""
    raise NotImplementedError


@pytest.mark.skip(reason="orchestrator not yet ported from old setup")
def test_run_campaign_stops_promptly_on_stop_flag():
    raise NotImplementedError
