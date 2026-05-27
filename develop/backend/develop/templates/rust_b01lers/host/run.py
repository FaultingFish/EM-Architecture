"""Host-side experiment driver for this project.

Imported by Control's orchestrator when a campaign references this
project. Implements the three lifecycle hooks below. `ctx` exposes:
  ctx.scaffold   — adapters.scaffold.ScaffoldAdapter
  ctx.shouter    — adapters.chipshouter.ChipShouterAdapter
  ctx.params     — current SweepParams snapshot
  ctx.logbook    — control.logbook.Logbook
  ctx.state      — control.state.AppState (read-only references)
"""


def setup(ctx) -> None:
    """Called once before the campaign starts. Configure DUT
    power, trigger mode, etc."""
    # Standard Scaffold pin map:
    #   D0 = USER_TEST (PA21)       — trigger: rising edge = test loop start
    #   D1 = USER_HEARTBEAT (PB14)  — read: toggled = heartbeat alive
    #   D2 = USER_LED_2 (PB10)      — read: rising edge = fault detected
    #   D3 = USER_LED_3 (PB9)       — read: falling edge = campaign end
    sc = ctx.scaffold
    sc.set_d0_output()      # D0 drives the trigger
    sc.set_d1_input()       # D1 reads heartbeat
    sc.set_d2_input()       # D2 reads fault flag
    sc.set_d3_input()       # D3 reads campaign-complete flag


def attempt(ctx) -> dict:
    """Called once per glitch attempt. Returns
        {"fault": bool, "heartbeat_alive": bool,
         "campaign_complete": bool}
    Reuses the Verdict shape from emfi_protocol.runs."""
    sc = ctx.scaffold

    # Pulse D0 high to start the test loop on the target
    sc.set_d0(1)
    sc.set_d0(0)

    # Wait for the target to respond
    import time
    time.sleep(ctx.params.delay_us / 1_000_000 if ctx.params.delay_us else 0.001)

    fault = bool(sc.read_d2())
    heartbeat_alive = bool(sc.read_d1())
    campaign_complete = not bool(sc.read_d3())

    return {
        "fault": fault,
        "heartbeat_alive": heartbeat_alive,
        "campaign_complete": campaign_complete,
    }


def teardown(ctx) -> None:
    """Called once after the campaign ends. Power-down DUT,
    restore safe state."""
    sc = ctx.scaffold
    sc.set_d0(0)
