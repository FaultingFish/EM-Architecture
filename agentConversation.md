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
