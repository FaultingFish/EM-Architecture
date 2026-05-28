"""Host-side experiment driver for this project.

Imported by Control's orchestrator when a campaign references this
project. Implements the three lifecycle hooks below. `ctx` exposes:
  ctx.scaffold   — adapters.scaffold.ScaffoldAdapter
  ctx.shouter    — adapters.chipshouter.ChipShouterAdapter
  ctx.params     — current SweepParams snapshot (dict or namespace)
  ctx.logbook    — control.logbook.Logbook
  ctx.state      — control.state.AppState (read-only references)

Uses ScaffoldAdapter's generic pin methods (set_d_output, set_d_input,
write_d, read_d) — portable across Scaffold pin counts. The narrow
aliases (set_d0_output, write_d0, read_d2, …) still work but the
generic form is preferred.

Pin map (target firmware side):
  D0 = USER_TEST (PA21)       — trigger: rising edge = test loop start
  D1 = USER_HEARTBEAT (PB14)  — read: toggled = heartbeat alive
  D2 = USER_LED_2 (PB10)      — read: rising edge = fault detected
  D3 = USER_LED_3 (PB9)       — read: falling edge = campaign end
"""


def setup(ctx) -> None:
    """Called once before the campaign starts. Configure DUT power,
    trigger mode, etc."""
    sc = ctx.scaffold
    sc.set_d_output(0)   # D0 drives the trigger
    sc.set_d_input(1)    # D1 reads heartbeat
    sc.set_d_input(2)    # D2 reads fault flag
    sc.set_d_input(3)    # D3 reads campaign-complete flag


def attempt(ctx) -> dict:
    """Called once per glitch attempt. Returns
        {"fault": bool, "heartbeat_alive": bool,
         "campaign_complete": bool}
    Reuses the Verdict shape from emfi_protocol.runs."""
    sc = ctx.scaffold

    # Pulse D0 high to start the test loop on the target
    sc.write_d(0, 1)
    sc.write_d(0, 0)

    # Wait for the target to respond; ctx.params may be a dict (orchestrator
    # snapshot) or an attribute-style object — handle both.
    import time
    if isinstance(ctx.params, dict):
        delay_us = ctx.params.get("delay_us")
    else:
        delay_us = getattr(ctx.params, "delay_us", None)
    time.sleep((delay_us or 1) / 1_000_000)

    return {
        "fault": bool(sc.read_d(2)),
        "heartbeat_alive": bool(sc.read_d(1)),
        "campaign_complete": not bool(sc.read_d(3)),
    }


def teardown(ctx) -> None:
    """Called once after the campaign ends. Power-down DUT, restore
    safe state."""
    ctx.scaffold.write_d(0, 0)
