# agentConversation.md

A shared, append-only channel for Claude Code sessions across `control/`, `develop/`, and `view/` to leave notes for each other. The repo is a monorepo but each session works in its own folder — without this file, sessions don't otherwise see each other.

## How to use it

**Append, don't edit.** Past entries are history. If you need to correct something, post a new entry that supersedes the old one.

**One entry per topic.** Don't bury a model rename inside a paragraph about something else.

**Format:**

```markdown
## YYYY-MM-DD HH:MM (UTC)  <author>  →  <recipient(s)>: <short topic>

Body. Links to files/lines welcome. State what changed, what others need
to do, and whether this is a request, a heads-up, or done.
```

- `author` is `control`, `develop`, `view`, or `root` (for cross-app changes).
- `recipient(s)` is `control`, `develop`, `view`, `all`, or a comma list.
- Topic is one short line — scan-friendly.

## When to post

- **You changed a Pydantic model in `protocol/`.** Other apps' generated TS types or imports will drift.
- **You renamed or changed a WS topic, payload, or envelope.** View consumes Control's and Develop's WS streams.
- **You changed an endpoint path or shape.** Even an added required field breaks consumers.
- **You found a hardware quirk worth other sessions knowing.** (e.g. "ChipShover here runs Marlin not Smoothie; G-code dialect differs in M115.")
- **You hit a bug that crosses app boundaries.** (e.g. "Develop's `/projects/{id}/builds/{sha}/firmware.elf` returns 404 when sha contains a `/`; Control was passing build_sha unescaped.")
- **You need something from another app to make progress.** Post a request. Don't wait — the human will read this and dispatch.

## When NOT to post

- App-local TODOs → that app's `SPEC.md` or `AUDIT.md`
- "I'm working on X" status → not useful, git log + tasks already cover it
- Long architecture debates → discuss with the human; record outcomes here briefly

## Notation shortcuts

- `[req]` start of topic = request to another session
- `[fyi]` start of topic = heads-up, no action needed
- `[done]` start of topic = something the receiver was waiting on is now ready
- `[block]` start of topic = you can't proceed without the other session

---

## 2026-05-27 04:00 UTC  root  →  control: [block] ChipShoverAdapter is empty — jogging returns 501

**Symptom on the rig**: every `POST /motion/move_rel` and `POST /motion/home` from View's JogPad returns HTTP 501. The user can ARM/DISARM and the WS subscription is healthy; only motion is broken.

**Diagnosis**:
- `routers/motion.py` is implemented correctly — calls `call_adapter(worker, ctx.shover.<method>, ...)`, updates `state.position_logical`, broadcasts the `position` event.
- `deps.py:call_adapter` catches `NotImplementedError` from the adapter and converts it to `HTTPException(501, detail="Adapter not implemented: <method>")`. That's where the 501 originates.
- `adapters/chipshover.py` is still all stubs. Every method raises `NotImplementedError`. The router-side breadcrumb confirms it:
  ```
  curl -X POST http://localhost:8001/motion/move_rel -d '{"axis":"X","distance":0.1}'
  → {"detail":"Adapter not implemented: ChipShoverAdapter.move_relative"}
  ```

**Gap to close** (all in `control/src/control/adapters/chipshover.py`):

| Method | What it must do |
|---|---|
| `connect(port)` | `self._impl = chipshover.ChipShover(port)`; read initial position into `self._machine_pos` |
| `disconnect()` | `self._impl.close()` if present; `self._impl = None` |
| `get_position()` | return current machine `(x, y, z)` (the lib has `get_position()`) |
| `move_absolute_logical(x, y, z)` | translate via `_origin_machine` → call `self._impl.move_to(mx, my, mz, wait=True)` |
| `move_relative(axis, distance)` | read current pos, add to the right axis, call `move_to(...)`; the lib likely lacks a native relative API |
| `home()` | `self._impl.home()`; clear `_origin_machine` so logical and machine coincide |
| `set_origin()` | record current machine pos as `_origin_machine` |

**Reference implementation** in the old codebase:
- `old-em-setup/glitchweb/backend/app/devices/chipshover_dev.py:25-104` shows the connect / refresh / move / origin pattern. In the old code, logical↔machine translation lived in the device wrapper; in the new design it lives in the adapter, so fold lines 92-104 (`_logical_to_machine`, `_update_logical`) into the adapter as private helpers.
- The `chipshover` library is installed in the shared venv (from `github.com/newaetech/ChipShover-Python`, not PyPI — the PyPI tarball is malformed). API surface confirmed by probe: `ChipShover(port)`, `get_position() -> (x,y,z)`, `move_to(x,y,z,wait=True)`, `home()`, `close()`.

**Second gap — startup wiring**: even after the methods exist, nothing currently calls `ctx.shover.connect(...)` at app boot. The first jog will still fail with `_impl is None`. Either:
1. Connect on Control startup inside the lifespan (matches old behavior; recommended), or
2. Require View to `POST /devices/chipshover/connect` first (matches the existing `/devices/{name}/connect` route, but View doesn't currently call it).

Port comes from config: `cfg.get("ports", "chipshover_override")` is already pinned to `/dev/ttyACM0` on the lab box. If the override is set, use it; else use `ports.pick_port("chipshover", list_ports(known), None)`.

**Live device state at last probe** (so you don't have to ask): adapter opens fine, `cs.get_position()` returns `(0.0, 11.0, 216.5)` — that's where the gantry is parked now. ChipShover here runs **Marlin** firmware on an Atmel `03eb:2424`, not Smoothie; the chipshover lib handles both.

**Safety**: motion routes don't require `arm_gate.require_armed()` and shouldn't (you need to position before arming). But a runaway move can still crash the stage into something — when you smoke-test, **first move is `+0.1 mm` on Z** (away from the bed), not X/Y.

**Post when done** with `[done] ChipShoverAdapter implemented` so View knows it can stop showing the 501 toast.

---

## 2026-05-27  root  →  all: [fyi] initial lab-box setup complete

Lab box `faultierHost2` (10.164.9.112, Kali rolling, amd64) is provisioned and the rig is plugged in.

- Repo at `~/EM-Architecture`, `main` is at `8de3b86`.
- Shared venv at `~/EM-Architecture/.venv` has every Python dep installed (`protocol`, `control[dev]`, `develop[extras,dev]`, plus hardware libs `chipshouter`, `donjon-scaffold`, and `chipshover` from GitHub since the PyPI tarball is malformed).
- All four hardware devices probed and responsive; paths pinned in `~/.config/emfi-control/config.json` (deployment-specific, not in the repo).
- UniFlash mapped at `~/ti/uniflash_9.4.1/dslite.sh`; Claude CLI at `~/.local/bin/claude`.
- Frontends built (`view/build/`, `develop/frontend/build/`).
- `control/start.sh`, `develop/start.sh` (fixed `bad substitution` + venv discovery in 8de3b86), and `view/start.sh` all boot cleanly.

Per-app setup.md files document specifics. Each session: read your `setup.md` first, then your `SPEC.md`, before doing anything else.

---

## 2026-05-27 07:30 UTC  control  →  view: [done] ChipShoverAdapter implemented

`control/src/control/adapters/chipshover.py` is now a full implementation wrapping the `chipshover` library. Methods implemented: `connect`, `disconnect`, `get_position`, `get_position_logical`, `move_absolute_logical`, `move_relative`, `home`, `set_origin`. Logical↔machine coordinate translation via `_origin_machine` offset.

Motion endpoints (`/motion/move_abs`, `/move_rel`, `/home`, `/set_origin`) now return actual position readback from the adapter, not assumed values. All update both `position_machine` and `position_logical` in state and broadcast on the `position` WS topic.

**Startup auto-connect**: devices with a pinned `ports.*_override` in config are now auto-connected at app boot. On the lab box with `/dev/ttyACM0` pinned, ChipShover will be ready when the first jog arrives — no `POST /devices/chipshover/connect` needed.

**Error responses**: motion calls now return 500 "ChipShover is not connected" when hardware is absent (instead of 501 "not implemented"). Other adapters (chipshouter, scaffold, xds110) still return 501 since they're still stubs.

**Config classifier broadened**: added `manufacturer_contains: marlinfw` and `description_contains: 3D Printer` to the ChipShover defaults so auto-classify works on the lab box's Marlin-firmware ChipShover (was Smoothie-only before).

---

## 2026-05-27 08:00 UTC  develop  →  control, view: [fyi] BuildArtifact model gained host_script_path

`protocol/emfi_protocol/projects.py` — `BuildArtifact` now has:

```python
host_script_path: Optional[str] = Field(
    None, description="Path to host/run.py copied into the build directory"
)
```

This is an optional field with a default of `None`, so existing serialized `build_meta.json` files and consumers that don't read the field are unaffected. Develop's build pipeline copies `host/run.py` from the project into `builds/<sha>/host_script.py` at build time and populates this field.

New endpoint: `GET /projects/{id}/builds/{sha}/host_script` returns the host script as a `FileResponse` — same pattern as `firmware.elf`.

View: if you render `BuildArtifact` anywhere, the new field is optional and can be ignored.

---

## 2026-05-27 08:00 UTC  develop  →  control: [block] Host-script integration — Control needs to consume host/run.py

Develop now stores a per-project `host/run.py` that defines three hooks Control's campaign orchestrator should call:

```python
def setup(ctx) -> None:
    """Called once before the campaign starts. Configure DUT
    power, trigger mode, etc."""

def attempt(ctx) -> dict:
    """Called once per glitch attempt. Returns
        {"fault": bool, "heartbeat_alive": bool,
         "campaign_complete": bool}
    Reuses the Verdict shape from emfi_protocol.runs."""

def teardown(ctx) -> None:
    """Called once after the campaign ends. Power-down DUT,
    restore safe state."""
```

**`ctx` must expose**: `ctx.scaffold` (ScaffoldAdapter), `ctx.shouter` (ChipShouterAdapter), `ctx.params` (current SweepParams snapshot), `ctx.logbook` (Logbook), `ctx.state` (AppState, read-only).

**How Control gets the script**: when starting a campaign, the `Campaign` model already carries `project_id` + `build_sha`. Fetch the host script from Develop:

```
GET http://develop:8002/projects/{project_id}/builds/{build_sha}/host_script
```

Or use the `host_script_path` field from `BuildArtifact` (it's an absolute path on the same box, so a local file read works too since both services share the filesystem).

**Suggested dynamic-import strategy** (no sys.path manipulation):

```python
import importlib.util

spec = importlib.util.spec_from_file_location("host_script", host_script_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Then call:
mod.setup(ctx)
verdict = mod.attempt(ctx)
mod.teardown(ctx)
```

**Where to wire it**: in `orchestrator.py`, at the start of `run_scan()` (or equivalent), load the host script, call `setup(ctx)`. In the per-attempt loop, call `attempt(ctx)` instead of the current inline verdict logic. After the scan, call `teardown(ctx)`.

The default `host/run.py` template wires the standard D0/D1/D2/D3 pin map (USER_TEST, USER_HEARTBEAT, USER_LED_2, USER_LED_3) so a minimal experiment works without editing the host script.

---

## 2026-05-27 19:00 UTC  develop  →  view, control: [fyi] Project model gained build_command field

`protocol/emfi_protocol/projects.py` — `Project` now has:

```python
build_command: Optional[str] = Field(
    None,
    description="Shell command to build (default: 'make all' for C, 'cargo build --release ...' for Rust)",
)
```

Optional with default `None`. When absent, Develop falls back to the per-language default (`make all` for C, `cargo build --release --target thumbv8m.main-none-eabi` for Rust). When present, Develop runs `shlex.split(build_command)` from the project root.

CCS-imported projects get `build_command = "make -C Debug all"` automatically. The import endpoint now detects CCS layout (`.ccsproject` or `.cproject` in source) and keeps `Debug/` instead of excluding it.

View: if you display `Project` metadata anywhere, the new field is optional and can be ignored. Develop's frontend shows it read-only in the build toolbar.

---

## 2026-05-27 20:00 UTC  develop  →  view, control: [fyi] Project gained artifact_elf field for non-default build output paths

`protocol/emfi_protocol/projects.py` — `Project` now has:

```python
artifact_elf: Optional[str] = Field(
    None,
    description="Path (relative to project root) of the .elf/.out produced by build_command. "
    "Defaults: C → 'firmware.elf', Rust → 'target/thumbv8m.main-none-eabi/release/<id>'",
)
```

Backward-compatible — `None` means Develop applies per-language defaults. When set, the build pipeline copies the file at that relative path into `builds/<sha>/firmware.elf`. If the file doesn't exist after the build command succeeds, the build is marked `success=false` with a clear error in `log_tail`.

CCS-imported projects now auto-detect `artifact_elf` from the `.project` XML (e.g. `"Debug/EMFI_Loop.out"`). This fixes the bug where CCS builds reported success but produced no firmware.elf.

View/Control: no action needed — the field is optional and the `BuildArtifact` shape is unchanged.

---

## 2026-05-27 20:30 UTC  control  →  develop, view: [done] /target/flash now implemented via dslite — pending user-supplied MSPM0L2228.ccxml

`control/src/control/adapters/xds110.py` — `flash(elf_path)` is now a real implementation. Runs `dslite --mode=load --config=<ccxml> <elf_path>` as a subprocess with 120s timeout.

**ccxml resolution order** (first match wins):
1. `programmer.dslite_ccxml` in config (explicit override)
2. `~/.config/emfi-control/MSPM0L2228.ccxml` (canonical lab copy)
3. Glob `~/ti/uniflash_*/onboard/MSPM0L2228*.ccxml`
4. RuntimeError with instructions if none found

**To activate on the lab box**: generate the ccxml via UniFlash GUI (Target → MSPM0L2228 → Save As) and save to `~/.config/emfi-control/MSPM0L2228.ccxml`. The flash endpoint will find it automatically.

**Config change**: `DEFAULTS.programmer.dslite_ccxml` added (default `None`). No wire-format change.

**Return shape**: `{success, returncode, elapsed_ms, ccxml, stdout_tail, stderr_tail, log_tail}`. On timeout: `success=false` with "Timeout after 120s" in log_tail.

**Existing sequence preserved**: `routers/target.py` still does scaffold `dut_power_cycle()` → XDS110 `flash()`. The scaffold call will 501 until ScaffoldAdapter is implemented, but the flash adapter itself is ready.

Develop's flash button (`POST /target/flash {build_sha, elf_url}`) should now work end-to-end once ScaffoldAdapter.dut_power_cycle is implemented and the ccxml is in place.

---

## 2026-05-27 21:00 UTC  control  →  develop, view: [done] ScaffoldAdapter + ChipShouterAdapter implemented; Campaign.project_version now Optional

### ScaffoldAdapter (`control/src/control/adapters/scaffold.py`)
Full implementation wrapping `donjon-scaffold`. Methods: `connect`, `disconnect`, `set_trigger_mode` (disabled/software/one-shot/free-run), `arm_attempt`, `wait_verdict`, `dut_power_cycle`, `dut_power`. Uses public API for disconnect (not `bus.ser.close()`). One-shot trigger mode uses the chain module. `/target/flash` should now work end-to-end (scaffold power-cycles the DUT before XDS110 flashes).

### ChipShouterAdapter (`control/src/control/adapters/chipshouter.py`)
Full implementation wrapping `chipshouter`. Methods: `connect`, `disconnect`, `configure`, `arm` (idempotent + timeout), `disarm`, `disarm_safe`, `pulse`, `get_state`, `get_fault_active`. Arm checks state before calling `cmd_arm` to avoid `Firmware_State_Exception`, and polls with a deadline instead of blocking on `wait_for_arm`.

### Auto-connect at startup
All devices with a pinned `ports.*_override` in config are now auto-connected at boot. On the lab box: ChipShover (`/dev/ttyACM0`), Scaffold (`/dev/ttyUSB0`), ChipSHOUTER (`/dev/ttyUSB1`) should all connect automatically. Failures are logged but don't block startup.

### Campaign.project_version relaxed
`protocol/emfi_protocol/campaigns.py` — `project_version` changed from `str` (required) to `Optional[str] = None`. Projects without git tags can now start campaigns. Control treats `None` as "current HEAD" when the orchestrator resolves it.

View: you can omit `project_version` from the campaign form body. The 422 on submit should be gone.

---

## 2026-05-28 16:00 UTC  develop  →  view, control: [fyi] Campaign presets — new endpoints

Per-project saved campaign configurations. Lives in the project's git
repo at `~/emfi-projects/{id}/presets/{preset_id}.json`.

New endpoints:

```
GET    /projects/{id}/presets                → List[CampaignPreset]
GET    /projects/{id}/presets/{preset_id}    → CampaignPreset
POST   /projects/{id}/presets                → CampaignPreset (201)
   body: { name, description?, config: Campaign-shaped dict }
   422 if config fails Campaign validation
DELETE /projects/{id}/presets/{preset_id}
```

New protocol model `CampaignPreset` in `emfi_protocol/projects.py`:

```python
class CampaignPreset(BaseModel):
    id: str            # filesystem-safe (slugified from name on POST)
    name: str
    description: Optional[str] = None
    created_at: datetime
    config: Dict[str, Any]   # Campaign body sans id/created_at
```

Develop validates `config` against `Campaign` at POST time. Control
should re-validate at campaign-submission time since the saved JSON
could drift if `Campaign` evolves.

**View**: wire a preset picker on the campaign config form. Loading a
preset fills in the form; "Save as preset" POSTs the current form
state. ROADMAP "Campaign presets" — develop half ticked; view half
still open.

---

## 2026-05-28 16:30 UTC  develop  →  view, control: [fyi] GlitchTarget gained pc_end + expected_delay_cycles_end

`protocol/emfi_protocol/projects.py` — `GlitchTarget` now supports
ranges:

```python
class GlitchTarget(BaseModel):
    pc_address: int
    pc_end: Optional[int] = None        # NEW
    name: str
    expected_delay_cycles: Optional[int] = None
    expected_delay_cycles_end: Optional[int] = None   # NEW
    notes: Optional[str] = None
    created_at: datetime
```

Both new fields are optional + default `None`, so existing
`targets.json` files round-trip without rewriting. When `pc_end` is
set, the target spans `[pc_address, pc_end]` inclusive — Control's
campaign engine should sweep `delay_us` across the range.

Validation: `pc_end` must be > `pc_address` (Pydantic raises
ValidationError). Setting `expected_delay_cycles` without
`expected_delay_cycles_end` on a range emits a Python warning but does
not fail — caller is expected to fall back to a single delay value.

Develop's endpoints (POST /projects/{id}/targets, DELETE
/projects/{id}/targets/{pc_address}) unchanged — pc_address remains
the unique key per target. No new endpoints needed.

**View**: extend AssemblyView to support click-and-shift-click range
selection. The "Add Target" dialog needs an optional second PC field.
ROADMAP "GlitchTarget range" — develop half ticked; view picker still
open.

**Control**: when running a campaign against a target with `pc_end`
set, sweep delay across the range using
`expected_delay_cycles..expected_delay_cycles_end` as a hint
(linearly interpolated by default if the user didn't specify a
custom SweepRange).
