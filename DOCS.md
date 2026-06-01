# DOCS — using and troubleshooting the EMFI platform

This is the operator's guide. It assumes you've followed [`INSTALL.md`](./INSTALL.md) and the three services are running.

If you want the *system design* rationale, read [`ARCHITECTURE.md`](./ARCHITECTURE.md) instead.

---

## 1. Mental model

You drive everything from **View** (`http://lab-box:8003/`). View is the only thing humans touch.

```
You ──> View (8003) ──HTTP/WS──> Control (8001) ──USB──> hardware
            └─────────HTTP/WS──> Develop (8002) ──fs──> firmware projects
```

- **Control** owns hardware. It is a singleton. If a second process tries to open the same serial port, you get a permission error.
- **Develop** owns firmware. Pure software. Talks to nothing but disk + git + toolchain.
- **View** is stateless. Multiple tabs are fine; whichever one is active "sees" the same truth Control publishes.

---

## 2. A first campaign, end to end

1. **Stand at the rig.** Visually confirm: ChipSHOUTER tip aligned roughly over the DUT, plenty of clearance, nothing flammable on the bed.
2. **Open** `http://lab-box:8003/`. Confirm the header shows `safe` (not ARMED) and that the four device cards show `connected`.
3. **Develop** — pick or create a firmware project at `http://lab-box:8002/`. Build it. The build produces a content-hashed artifact under `~/emfi-projects/<id>/builds/<sha>/`.
4. **Open the assembly view** for that build. Click the instruction you want to glitch — that's your "target PC". The UI computes an expected delay window from the PC offset.
5. **View → New campaign**:
   - Pick the project + version (Develop list).
   - Pick the target PC (set in step 4) or leave blank for area sweep.
   - **Grid**: set origin and top-right of the XY region you want to scan; z range if relevant.
   - **Sweep**: set delay range / pulse-width range / voltage range. Default `attempts_per_point=1` keeps it fast; raise to 5–10 if you suspect probabilistic faults.
   - Submit.
6. **Hold-to-ARM.** This is a 1-second hold on the ArmButton (touch or mouse). The header turns red and says ARMED. The auto-disarm countdown starts.
7. **Watch the live campaign view.** 3D scene tracks the stage; LogTail shows attempt outcomes as they happen; the heatmap updates.
8. **Stop conditions**: campaign finishes naturally, you hit STOP (or Esc/Space), or auto-disarm fires after 5 minutes of inactivity.

After: open `/runs` to filter by outcome, click a row to see details, or click **Replay** to re-fire that exact attempt.

---

## 3. Where data lives

| Thing | Path |
|---|---|
| Control config | `~/.config/emfi-control/config.json` |
| JSONL logbook (canonical) | `~/.local/share/emfi-control/sessions/logbook-YYYYMMDD.jsonl` |
| SQLite query index | `~/.local/share/emfi-control/sessions/index.sqlite` |
| Dangerous-action audit log | `~/.local/share/emfi-control/audit/audit-YYYYMMDD.jsonl` |
| Last flashed DUT provenance | `~/.local/share/emfi-control/flashed_firmware.json` |
| Firmware projects | `~/emfi-projects/<project-id>/` |
| Per-build artifacts | `~/emfi-projects/<project-id>/builds/<sha>/` |
| Project version history | `~/emfi-projects/<project-id>/.git/` |
| systemd service logs | `journalctl -u emfi-{control,develop,view}` |
| Old reference codebase | `~/EM-Architure/old-em-setup/` (read-only — do not edit) |

The JSONL is the source of truth. If the SQLite mirror gets out of sync (deleted manually, schema changed, ...) rebuild it:

```bash
python -m control.tools.reindex
```

---

## 4. Troubleshooting matrix

| Symptom | Likely cause | Fix |
|---|---|---|
| `GET /devices` shows everything `connected: false` | User not in `dialout` group | Add and re-login (see INSTALL §2) |
| One specific device is `connected: false` while others work | VID/PID classifier didn't match, or override path is wrong | Check `known_devices` and `ports.*_override` in `config.json`; verify with `lsusb` and `python -m serial.tools.list_ports -v` |
| Pulses don't fire; no error | ArmGate is closed | Hold to ARM; confirm header flips to red. Auto-disarm may have fired |
| `Rate limit on 'shouter': 10.0 per second exceeded` | RateLimiter doing its job | Increase `safety.max_pulses_per_sec` if you're certain the hardware can sustain it. Default 10/s is the documented safe rate |
| `Firmware_State_Exception` from ChipSHOUTER | Library tried to arm an already-armed device | Should be guarded by idempotent `arm()`. If still happening, file as a Control bug — the carry-forward fix is at `old-em-setup/HANDOFF.md` "ChipSHOUTER A0 freakout / re-arm" |
| ChipSHOUTER appears hung after ARM | `wait_for_arm()` infinite block when HV doesn't come up | Power-cycle ChipSHOUTER. The mitigation (timeout + abort) is a known carry-forward fix; verify it's in `control/src/control/adapters/chipshouter.py:arm()` |
| Scaffold won't reconnect after a hang | Old setup had a fragile `bus.ser.close()` call | Power-cycle Scaffold. Make sure `adapters/scaffold.py` uses the upstream lib's public close, not the internal attribute |
| Trigger fires but no glitch ever detected | Trigger mode mismatch | In campaign config, confirm `trigger_mode` matches your wiring: `software` (USB-fired) needs ChipSHOUTER USB connected; `one-shot`/`free-run` needs the A0 cable physically present |
| Hangs detected every attempt with no glitches | Verdict timeout too short OR DUT not actually running | Increase `verdict_timeout_ms`; on the bench, confirm the target firmware actually toggles D1 (heartbeat) when running. Use OpenOCD to step through if needed |
| Flash via UniFlash fails with "device not found" | XDS110 needs the user in `plugdev` group, or `dslite_bin` path is wrong | See INSTALL §2 and §6 |
| OpenOCD attach hangs / "unable to open" | Another openocd is still running, or XDS110 is still claimed by dslite | `pkill openocd`; ensure no flash job is in flight; retry |
| Build fails: `arm-none-eabi-gcc: not found` | Toolchain not installed on lab box | `sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi` |
| Rust build fails: target not installed | Missing thumb target | `rustup target add thumbv8m.main-none-eabi` |
| Develop agent endpoint returns network error | `claude` CLI not installed or not logged in | Run `claude --version` as the service user; complete first-time auth |
| View shows stale data after browser tab was idle | WS dropped while browser slept | Refresh the page; reconnection-with-backoff is on the V2 list |
| Counters / position don't update on one tab | WS disconnected | Same as above; multiple tabs each hold their own WS |
| Heatmap is empty even though runs exist | SQLite index is missing the campaign | Run `python -m control.tools.reindex`. The JSONL is fine; the mirror just needs rebuilding |
| `pip install -e control/[hw]` fails on a non-Linux dev machine | Some hardware libs are Linux-only | Skip `[hw]` on dev machines; only install it on the lab box |

---

## 5. When to use OpenOCD vs UniFlash

- **UniFlash (dslite)** — fast, scripted, headless. Use for the normal **"flash → run a campaign"** loop. Control's `POST /target/flash` calls this.
- **OpenOCD** — interactive debugger session. Use when you want to **step through the target firmware in `arm-none-eabi-gdb` while glitching it** (combined SW + HW attack analysis). Control's `POST /target/debug_attach` spawns OpenOCD on configured ports; connect from your laptop with:
  ```bash
  arm-none-eabi-gdb firmware.elf -ex 'target extended-remote lab-box:3333'
  ```

Only one of them owns the XDS110 at a time. Detach the debugger before kicking off a flash.

---

## 6. Safety primitives — what they do and why

The Control service has three primitives that gate every pulse. If you fight them, you will damage hardware or hurt someone. Don't disable them.

- **ArmGate** — every pulse-emitting code path calls `arm_gate.require_armed()`. The user must hold-to-arm in View. The gate auto-disarms after `safety.auto_disarm_minutes` of inactivity (default 5).
- **RateLimiter** — sliding window. Default `safety.max_pulses_per_sec = 10`. Bursts beyond that raise `RateLimited`.
- **StopFlag** — campaign loops check this between every attempt. STOP / Esc / Space sets it; the loop exits cleanly.

If you ever see code that calls a pulse function without `require_armed()` upstream, file a bug. Carry-forward source: `old-em-setup/glitchweb/backend/app/safety.py` (now `control/src/control/safety.py`).

---

## 7. Logs and where to look first

In order of usefulness when something is wrong:

1. **journalctl** for each service: `journalctl -u emfi-control -f` (and `-develop`, `-view`). Most adapter errors show here with a `_format_error()` prefix.
2. **The JSONL logbook** for the run that misbehaved. `outcome`, `verdict`, `shouter_state`, `elapsed_ms` are all there.
3. **The audit JSONL** for mutating hardware/API actions such as arm, pulse, motion, power, flash, campaign start/stop:
   ```bash
   tail -f ~/.local/share/emfi-control/audit/audit-$(date -u +%Y%m%d).jsonl
   ```
4. **The browser console** in View for client-side issues (WS reconnect, type errors against API responses).
5. **Swagger UI** at `http://lab-box:8001/docs` lets you call any Control endpoint manually to isolate "is it the UI or the backend?"

Control also reads `~/emfi-projects/<project-id>/targets.json` at campaign
start. If a campaign sets `target_pc`, omits `sweep.delay_us`, and the matching
GlitchTarget has expected delay cycles, Control materializes `delay_us` from
that metadata. Range targets use `expected_delay_cycles` through
`expected_delay_cycles_end` at the build's cached `cpu_mhz`.

---

## 8. Resetting things

- **Clear a stuck arm state**: `POST /disarm` from Swagger, or restart Control.
- **Clear active campaign**: `POST /campaigns/{id}/stop`, then restart Control if it didn't release.
- **Wipe the SQLite index (keeps JSONL)**: delete `~/.local/share/emfi-control/sessions/index.sqlite` and run `python -m control.tools.reindex`.
- **Nuke a session's data** (rare; you really want the JSONL): move `logbook-YYYYMMDD.jsonl` aside and re-run reindex.
- **Reset View tab**: hard-refresh.

---

## 9. What is NOT in V1

The following are deliberately deferred. Don't be surprised they're missing:

- USB webcam overlay + click-to-jog calibration
- Continuous heartbeat watcher (V1 only watches between attempts)
- Delta-encoded WS state broadcasts (V1 sends snapshots)
- Cross-rig comparison
- Cloud archive of JSONL
- Persistent ARM ("always on") mode for hands-off campaigns
- WS reconnection-with-backoff (current behavior: refresh the page)

These live in `ARCHITECTURE.md` § "Phase 2 deferrals". File them as features if you decide they're needed.

---

## 10. Getting help

- Per-app contracts: `control/SPEC.md`, `develop/SPEC.md`, `view/SPEC.md`.
- Short runbooks and wiki index: `docs/wiki/index.md`.
- New-laptop development migration: `setup.md`.
- Architecture rationale + the carry-forward catalog: `ARCHITECTURE.md`.
- Bug history from the old codebase (worth a read for any weird hardware behavior): `old-em-setup/HANDOFF.md`.
- Audit reports from initial scaffold: `develop/AUDIT.md`, `view/AUDIT.md`.
- AI/agent session notes: `agentsNotes.md`.
