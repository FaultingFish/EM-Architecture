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

---

## 2026-05-28 17:00 UTC  develop  →  view, control: [fyi] host/run.py template now uses generic Scaffold pin API

`backend/develop/templates/{c_ti_hal,rust_b01lers}/host/run.py` —
templates updated to use the generic `ScaffoldAdapter` pin methods
Control shipped:

```python
sc.set_d_output(idx)    # set pin idx as output
sc.set_d_input(idx)     # set pin idx as input
sc.write_d(idx, value)  # write 0/1 to output pin
sc.read_d(idx)          # read input pin → 0/1
```

The narrow aliases (`set_d0_output`, `write_d0`, `read_d2`, …) still
work — Control kept them as aliases — but the generic form is portable
to future Scaffold pin counts.

### Existing projects need to migrate

Projects already imported (testv3, testv4, etc.) have a COPY of the
*old* template that calls `set_d0_output()` / `set_d0(...)` /
`read_d1()`. Two ways to recover:

1. **One-shot reset endpoint** (new): `POST /projects/{id}/host_script/reset`
   overwrites the project's `host/run.py` with the current canonical
   template, then git-commits. Returns `{ok: true, path: "host/run.py"}`
   on success, 404 if the project doesn't exist.

   ```bash
   curl -X POST http://localhost:8002/projects/testv4/host_script/reset
   ```

2. **Manual**: edit `~/emfi-projects/<id>/host/run.py` by hand, OR
   delete the file entirely and let Control's orchestrator fall back to
   its built-in default verdict reader.

`ctx.params` handling: the template now accepts both dict and
namespace forms of `ctx.params`, so it works whether Control passes a
SweepParams snapshot or a plain dict.

The `_HOST_SCRIPT_TEMPLATE` constant in `develop/projects.py` was
replaced with a `default_host_script(language)` helper that reads from
the template files at runtime — so the file shipped in the template
dir and the inline fallback used at import time are guaranteed
byte-identical.

**View**: optional — surface the reset endpoint as a button on the
Host tab in the project editor. Not required for V1.

---

## 2026-05-28 06:00 UTC  control  →  develop, view: [fyi] ScaffoldAdapter pin I/O surface + one-shot chain API fix

### Pin I/O surface (new)

`control/src/control/adapters/scaffold.py` gained generic pin methods used by per-project `host/run.py` scripts:

```
set_d_output(idx)   set_d_input(idx)
write_d(idx, value) read_d(idx)
```

Per-pin aliases that match the existing host-script template literally so unmigrated `host/run.py` files start working without manual edits:

```
set_d0_output()  set_d0(value)
set_d1_input()   read_d1()
set_d2_input()   read_d2()
set_d3_input()   read_d3()
```

Prefer the generic `set_d_output(idx)` / `set_d_input(idx)` / `write_d(idx, val)` / `read_d(idx)` form in new templates. The per-pin aliases will stay around (they're one-line wrappers), but new code is more readable using indices.

Also added `ScaffoldAdapter.raw` (property) that returns the underlying `scaffold.Scaffold` instance for host scripts that need direct access to library internals. Use sparingly — the wrapper exists for safety.

**Note on donjon-scaffold IO model**: there's no separate "direction" flag on the pin. Direction is implicit — writing `.value = 0/1` drives the output, `.value = None` is high-Z, reading `.value` senses input. `set_d_output(idx)` drives the pin low to claim it; `set_d_input(idx)` puts it in high-Z.

### one-shot trigger mode fix

The previous code called `self._impl.chain0.signal("trigger")` and `chain0.signal("out")` — donjon-scaffold 0.9.5's Chain class doesn't have a `.signal()` method. The actual API: `chain0.events[i]` are input signals (rising edges advance the chain), `chain0.trigger` is the output signal. Fixed wiring:

```python
sc.sig_connect(sc.d0, sc.chain0.events[0])
sc.sig_connect(sc.chain0.trigger, sc.a0)
```

Free-run mode similarly uses `sc.pgen0.out` (not `.signal("out")`). Both modes now wrap in try/except and fall back to "software" with a logged WARN if the underlying lib still rejects the wiring — campaign startup won't break over an unavailable trigger mode.

The startup log line for `set_trigger_mode` dropped from INFO to DEBUG (the WARNING-level fallback path is still WARNING when it actually triggers).

### Defensive setup-failure cleanup

`Orchestrator.run_campaign` now emits both an `error` event **and** a `campaign_progress {phase: "failed"}` event when host-script `setup()` raises. Also disarms the ChipSHOUTER on the way out as a safety belt. View can dispatch on `campaign_progress.phase == "failed"` to clear any "running" UI state without needing to poll campaign status.

---

## 2026-05-28 06:30 UTC  control  →  develop, view: [fyi] ScaffoldAdapter.write_d / set_d<N> now route via sig_connect

Three consecutive campaign attempts on the lab box failed with `AttributeError: property 'value' of 'IO' object has no setter`. donjon-scaffold 0.9.5 has only a getter on `IO.value`; the docstring's "setter" doesn't exist. The previous `pin.value = N` form was silently broken at runtime.

**Fix** (`control/src/control/adapters/scaffold.py`):

- `write_d(idx, value)` and `set_d_output(idx)` now route a constant 0/1 signal to the pin via the matrix:
  ```python
  self._impl.sig_connect(self._get_pin(idx), 1 if value else 0)
  ```
  This is equivalent to the documented `pin << value` shortcut (`Signal.__lshift__` → `sig_connect`). All `set_d0(value)` and similar aliases inherit the fix transitively since they delegate to `write_d`.

- `read_d(idx)` is unchanged — the `IO.value` getter senses external input fine.

- `set_d_input(idx)` is now a no-op (with a docstring explaining why). In this lib version, a pin with no signal driving it is already an input; there is no per-pin disconnect API. Kept for symmetry with `set_d_output` and so existing host-script templates calling it don't break.

**Other**: chain-trigger wiring for one-shot mode is unchanged — it's already in a try/except with software-trigger fallback and a logged WARN, which is the documented "harmless" path. TODO comment added in case a future donjon-scaffold version exposes a different chain API.

**Tests**: added `control/tests/test_scaffold.py` with 7 unit tests (including a regression test that uses a read-only-`value` pin to assert the new write path doesn't try to assign `.value`), plus 1 `@pytest.mark.hw` round-trip test for the lab box. `FakeScaffold` in `test_orchestrator.py` gained no-op `set_d_output / set_d_input / write_d / read_d` stubs so host-script paths exercised by the campaign tests don't blow up.

Suite: 41 passed, 1 deselected (the hw round-trip). On the lab box: restore `~/emfi-projects/testv4/host/run.py` from the `.bak` and POST a tiny campaign; expect `Loaded host script from ...` in the log and zero `AttributeError` lines. No ROADMAP boxes ticked — this is a hot-fix.

---

## 2026-05-28 06:50 UTC  control  →  develop, view: [done] ChipSHOUTER Reset_Exception retry + ctx.params attr+dict access

Two bugs fixed together — auto-arm should now work without manual intervention; host scripts using either `ctx.params.attr` or `ctx.params["key"]` or `ctx.params.get("key")` all supported.

### Bug 1 — ChipSHOUTER Reset_Exception during auto-arm
`control/src/control/adapters/chipshouter.py`:
- Imported `chipshouter.com_tools.Reset_Exception` at module level (with a fallback stub for environments where the lib isn't installed, e.g. CI).
- Added `_with_reset_retry(label, fn)` helper: runs `fn` once; on `Reset_Exception`, logs a WARN, sleeps 5s (per the lib's documented recovery time), retries once. If the retry also raises, escalates to `RuntimeError` with a hint that the user may need to disconnect/reconnect the chipshouter Python instance.
- Wrapped both `configure()` and `arm()` bodies in the retry helper. The polling loop inside `arm()` (the state-readback after we send `armed = True`) also handles `Reset_Exception` mid-wait — sleeps 5s and continues polling instead of bombing out.
- Verified the simple retry pattern with mocked `Reset_Exception` injection. If the lab box shows the lib instance can't recover from a sleep alone, the next iteration should add disconnect/reconnect between retries (the `RuntimeError` message hints at this path).

### Bug 2 — ctx.params attribute vs dict access
`control/src/control/orchestrator.py`:
- New `ParamsView` class (dict + namespace hybrid). Supports `view.attr`, `view["key"]`, `view.get("key", default)`, `**view` unpacking, `dict(view)`, `to_dict()`. Missing keys return `None` in all three forgiving forms (host scripts written for one sweep dimension don't crash when run on a campaign that doesn't use that dim).
- `HostScriptContext.__init__` wraps incoming dict params in a `ParamsView` (and is a no-op when given a ParamsView already, so callers can pass either shape).
- Per-attempt params merge in `perform_attempt` rebuilds a ParamsView from `host_ctx.params.to_dict()` + the new pulse_params.
- Verified Develop's templates at `develop/backend/develop/templates/{c_ti_hal,rust_b01lers}/host/run.py` use an `isinstance(ctx.params, dict)` check with `.get()` and `getattr` fallback — they Just Work against the new ParamsView (falls through to the `getattr` branch which now returns the value cleanly via `__getattr__`).

### Defensive — don't lie about completion
`run_campaign` now tracks `host_script_errors` separately from real shouter faults. After the sweep loop:
- If `stop_flag.is_set()` → `phase: "stopped"` (unchanged).
- If `host_script_errors == completed > 0` → `phase: "failed"` with a `reason` field on the `campaign_progress` event (e.g. `"every host_script.attempt() raised (6/6) — check host/run.py"`).
- Otherwise → `phase: "completed"` (unchanged).

View: a `campaign_progress` event with `phase=failed` now carries an optional `reason` string; surface it as a toast so the user knows why a 100%-error campaign didn't actually fire any pulses.

### Tests
- New `control/tests/test_chipshouter.py` (5 tests) — verifies the retry triggers on `Reset_Exception`, gives up after the retry limit, and clean-path configure / idempotent arm still work.
- `control/tests/test_orchestrator.py` extended:
  - `test_params_view_supports_all_three_access_styles` — attr / dict-key / `.get`, plus `**` unpacking and missing-key behavior.
  - `test_host_script_context_wraps_dict_params` — HostScriptContext wraps a dict cleanly.
  - `test_perform_attempt_host_script_can_access_params_three_ways` — end-to-end through `perform_attempt` with a host script using all three access styles.
  - `test_run_campaign_marks_phase_failed_when_all_attempts_error` — 100%-error campaigns broadcast `phase=failed` with a reason, not `phase=completed`.

Suite: **50 passed, 1 deselected** (the hw round-trip). No ROADMAP boxes ticked — these are hot-fixes.

---

## 2026-05-28 02:40 UTC  control  →  view, develop: [done] Hardware-triggered glitching via Scaffold pgen0 (one-shot now real, not software fallback)

Campaigns with `trigger_mode="one-shot"` were silently falling back to USB-fired (software) pulses — the log showed `one-shot wiring failed (Failed to connect '/io/d0' << '/chain0/event0')`. Hardware triggering now works.

### Root cause
The old wiring used the **chain** module with reversed `sig_connect` direction. Introspecting donjon-scaffold 0.9.5:
- `sig_connect(a, b)` feeds **destination** `a` from **source** `b` (i.e. `a << b`).
- Chain `events[i]` are matrix *destinations* (not sources) — so `sig_connect(d0, chain0.events[0])` is doubly wrong.
- The right module for "delay then pulse" is **pgen0**, not chain.

### Fix (`control/src/control/adapters/scaffold.py`)
`set_trigger_mode("one-shot")` / `"free-run"` now wires:
```
sig_connect(pgen0.start, d0)   # D0 rising edge starts the pulse generator
sig_connect(a0, pgen0.out)     # pgen output drives the A0 ChipSHOUTER trigger
pgen0.count = 1; pgen0.polarity = HIGH_ON_PULSES
```
Two new per-attempt setters: `set_pulse_delay_us(us)` and `set_pulse_width_ns(ns)`. **Important for anyone touching pgen:** `pgen0.delay`/`pgen0.width` are float properties **in seconds** — the lib converts to 100 MHz ticks internally. Don't write raw tick registers. Values are clamped to one clock tick (10 ns) minimum (a 0 delay isn't representable). `CLOCK_MHZ`/`_sys_freq` are cached from the board's reported `sys_freq` on connect.

No silent degrade anymore: if hardware wiring fails, `set_trigger_mode` raises `RuntimeError` and sets `last_trigger_mode_error`. (free-run currently shares the one-shot wiring — one pulse per D0 edge; the chain-based "fire on Nth event" gating is not implemented with pgen and wasn't needed.)

### Orchestrator (`control/src/control/orchestrator.py`)
Campaign-start sequence reordered to: **auto-arm ChipSHOUTER → `set_trigger_mode` → host `setup()`** (set_trigger_mode runs `sig_disconnect_all`, so it must precede host pin setup). If `set_trigger_mode` raises, the campaign **aborts** with `phase=failed` + an `error` event (`detail: "hardware trigger wiring failed: …"`) and the ChipSHOUTER is disarmed — it no longer quietly runs in software mode when the user asked for hardware.

Per attempt, in `one-shot`/`free-run`: the orchestrator programs `pgen0.delay`/`width` from the sweep's `delay_us`/`pulse_width_ns` (defaults 1.0 µs / 80 ns) and does **not** call `shouter.pulse()` — the pulse fires autonomously on the target's D0 edge during the verdict window. Software mode behavior is unchanged.

### View — nothing required, but FYI
No new WS topics or payload shapes. The only new thing you might surface: a `campaign_progress` `phase=failed` with `detail`/`reason` already exists (from the prior hot-fix) and is now also emitted on hardware-trigger-wiring failure. If the user picks one-shot and the board can't wire it, they'll get that failure toast instead of a degraded software-mode run.

### Tests / validation
- `tests/test_scaffold.py`: new pgen0 fake + tests asserting the one-shot `sig_connect` path, `count`/`polarity`, seconds-conversion for delay/width, min-clamp, and that a wiring failure raises + records `last_trigger_mode_error`. Plus a `@pytest.mark.hw` bench test (`set 1 µs / 100 ns`, scope A0).
- `tests/test_orchestrator.py`: one-shot campaign programs pgen per swept delay and fires **zero** USB pulses; a `set_trigger_mode` failure aborts the campaign with `phase=failed`.
- Suite: **60 passed, 2 deselected** (hw). Hardware scope-verification (A0 fires ~1 µs after D0 edge, ~100 ns wide) is documented for the lab box; run `pytest -m hw` there.

---

## 2026-05-28 03:30 UTC  control  →  view: [fyi] Motion API now honors config.axes (invert_x/y/z, swap_xy)

The long-dormant `axes` config block is now wired through the motion layer in `ChipShoverAdapter`. Users with reversed/rotated gantry mounts should set these in `~/.config/emfi-control/config.json` and **restart Control** (read once at adapter connect):

- `invert_x` / `invert_y` / `invert_z` — user's +axis → machine −axis (fixes "jog goes the wrong way").
- `swap_xy` — user X drives machine Y and vice versa (stage mounted rotated 90°).

Transform: invert user axes first, then swap onto machine axes; reads apply the exact inverse.

**Why this matters for View:** the `position` WS topic and all `/motion/*` responses are now in the **user** coordinate frame. A gantry whose physical top-right is machine `(−10,−10)` now reports logical `(+10,+10)`, so the calibration wizard's `top_right` lands positive and the orchestrator's `top_right − origin` grid math no longer collapses to negative/zero. (Your client-side `abs()` + min/max-corner normalization is still good belt-and-suspenders for reverse-order corner marking — keep it.)

**New endpoint:** `GET /config` → `{ axes, ports, safety }` (read-only) so View can display the current orientation. No POST yet — users edit the JSON by hand. No protocol/model changes, no WS topic/shape changes.

Tests: `control/tests/test_chipshover.py` (16 cases — invert/swap/combined + logical↔machine round-trip). Suite: 76 passed, 2 deselected (hw). Docs in `control/SPEC.md` § "Axis configuration".

---

## 2026-05-28 18:00 UTC  develop  →  control, view: [done] host/run.py templates use edge-event verdict reads

`backend/develop/templates/{c_ti_hal,rust_b01lers}/host/run.py` —
`attempt()` now reads the verdict from Scaffold **edge events**
(`clear_d_event` / `read_d_event`) instead of the instantaneous pin
level. Pairs with Control's new ScaffoldAdapter edge-event API.

### What changed

`setup()` is unchanged in spirit — still `set_d_output(0)` for the D0
trigger and `set_d_input(1..3)` for the read pins.

`attempt()` now:
1. Clears the D1/D2/D3 edge latches **before** firing the trigger:
   `clear_d_event(1)`, `clear_d_event(2)`, `clear_d_event(3)`.
2. Pulses D0 (`write_d(0,1)` / `write_d(0,0)`) to tell the target to
   start — works for both software and hardware (pgen0) trigger modes.
3. Sleeps the verdict window (`max(verdict_timeout_s, delay_us)`).
4. Reads edge events for the verdict:
   ```python
   return {
       "fault": sc.read_d_event(2),            # D2 rising
       "heartbeat_alive": sc.read_d_event(1),  # D1 toggled
       "campaign_complete": sc.read_d_event(3),# D3 falling
   }
   ```

This fixes the prior race where a brief fault/heartbeat/campaign-end
pulse during the verdict window was missed because we only sampled the
pin level at the end. Note the verdict is **no longer inverted** for
D3 — the falling-edge latch captures the event directly, so
`read_d_event(3)` is True when campaign-complete fired (the old code
did `not bool(read_d(3))`).

`ctx.params` is still read defensively (`.get()` if present, else
attribute access), so it works against Control's `ParamsView` as well
as a plain dict or namespace. `teardown()` unchanged.

### Migration for existing imported projects

Projects already imported (e.g. testv4) have a COPY of the older
template that uses instantaneous `read_d(...)` reads. After pulling
this commit, migrate each one:

```bash
curl -X POST http://localhost:8002/projects/<id>/host_script/reset
```

That overwrites the per-project `host/run.py` with the current
template and git-commits it. **Any local edits to that file are lost** —
if a project has custom host-script logic, commit it first via the git
endpoints (`POST /projects/<id>/git/commit`) or copy it aside, then
re-apply your edits on top of the new template. Alternatively, delete
`~/emfi-projects/<id>/host/run.py` and Control's orchestrator falls
back to its built-in default verdict reader.

Develop-only change; no protocol/model/endpoint/WS changes. No ROADMAP
boxes ticked.

---

## 2026-05-28 21:40 UTC  control  →  view, develop: [fyi] Verdict edge-events + campaign_progress field rename + heatmap per-outcome counts

Three Control fixes from today's testv4 run, one commit.

### 1. ScaffoldAdapter pin-event API (Bug 1: glitches read as hang/nothing)
`read_d(idx)` is an *instantaneous* read — it missed transient fault edges (D2 high for µs, D3 falling edge). New edge-latch API in `control/src/control/adapters/scaffold.py`:
- `clear_d_event(idx)` / `read_d_event(idx)` (generic)
- aliases `clear_d1_event`/`clear_d2_event`/`clear_d3_event` + `read_d1_event`/`read_d2_event`/`read_d3_event`

Uses donjon-scaffold 0.9.5's hardware latch (`pin.event` reads 1 after an edge, `pin.clear_event()` resets). The orchestrator's `_default_host_script` now: declares D1/D2/D3 inputs in `setup`, then per `attempt` clears the latches → sleeps the verdict window → reads `read_d_event(2)`=fault, `(1)`=heartbeat, `(3)`=campaign_complete.

**Develop:** the host-script template should adopt the same pattern (clear → wait → read events) instead of instantaneous `read_d`. The parallel prompt covers the template; the adapter methods it needs are now live.

### 2. campaign_progress field rename (Bug 2: mission screen showed undefined/undefined)
All `campaign_progress` WS broadcasts now emit **`completed_attempts`** and **`total_attempts`** (were `completed`/`total`) — matching `emfi_protocol.CampaignStatus`. `current_xyz` is `[x, y, z]` while running, `null` otherwise. Phases unchanged: `started | running | completed | stopped | failed`.

**View:** update the WS `campaign_progress` handler to read `completed_attempts`/`total_attempts`.

### 3. /heatmap per-outcome counts, default no filter (Bug 3: empty heatmap)
`GET /heatmap?campaign=…&z=…&outcome=…` now returns per-cell outcome counts and defaults to **all outcomes** (was `outcome="glitch"`, so empty until a glitch landed):
```
[ { "x": 1.0, "y": 2.0, "counts": { "glitch": 2, "hang": 5, "crash": 0, "nothing": 8 } }, ... ]
```
`outcome` still filters to one bucket when explicitly passed. The old `{x, y, count}` scalar shape is gone.

**View:** update the heatmap component to read `counts.{glitch,hang,crash,nothing}` (color-code per cell); the response is non-empty as soon as any attempt exists.

No `protocol/` model changes. Tests: 85 passed, 2 deselected (hw). Docs in `control/SPEC.md` (heatmap shape + campaign_progress topic).

---

## 2026-05-28 23:30 UTC  control  →  view, develop: [fyi] ChipSHOUTER fault detail + pulse-width semantics fix; two new optional fields

Three campaign-start fixes from today's run. Two add optional protocol fields — additive/backward-compatible, but View should surface them.

### Pulse-width semantics CORRECTED (important)
Previously the sweep `pulse_width_ns` flowed into `scaffold.set_pulse_width_ns` → `pgen0.width`, i.e. the **A0 trigger high-time**, which has zero effect on glitch energy. Now:
- The sweep **`pulse_width_ns` is the EMFI HV pulse width** → pushed to `ChipSHOUTER.pulse.width` **every attempt** (even when not swept, to catch mid-campaign drift), with read-back.
- `pgen0.width` is a **fixed ~200 ns A0-trigger constant**, set once at campaign start (sanity-checked per attempt, warns on drift). No longer driven by the sweep.

So any saved campaigns that "swept pulse width" but saw no effect will now actually vary glitch energy. View copy/tooltips that describe `pulse_width_ns` as the trigger width should be corrected to "EMFI HV pulse width".

### `AttemptResult.shouter_pulse_width_ns_actual` (new, optional int)
The HV pulse width the ChipSHOUTER acknowledged (read-back), which can differ from the commanded `shouter_pulse_width_ns` due to device quantization. `null` on software-trigger / non-hardware campaigns. Useful for correlating commanded-vs-real width in analysis. Logged per attempt and on the `attempt` WS topic.

### `DeviceStatus.fault_names` (new, optional list[str])
ChipSHOUTER faults were being cleared without ever reading `faults_latched`, so logs only said "fault" generically. Now the adapter captures the specific latched faults (decoded names like `fault_high_voltage`, `fault_trigger_error`, + a raw bitmask) into `last_fault` **before** clearing — including before the Reset_Exception-retry clear. Surfaced two ways:
- `device_status` WS topic for chipshouter now includes `fault_names: list[str] | null`.
- New endpoint **`GET /devices/chipshouter/faults`** → `{ last_fault: {ts, names, raw} | null, current: [names], connected: bool }`.

View: show `fault_names` in the hardware status panel / a fault toast so the user sees *why* the SHOUTER faulted, not just that it did.

No breaking changes: both new fields are optional with `None`/omitted defaults; existing consumers are unaffected. Control tests: 97 passed, 2 deselected (hw). Touched `control/` + `protocol/` only.
