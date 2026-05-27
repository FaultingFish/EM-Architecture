# Control — Spec

## Purpose

Single owner of all physical hardware on the lab rig. Exposes a REST + WebSocket API consumed by View (and optionally Develop, when Control needs to pull build artifacts).

## Invariants

1. **One process per rig.** Serial devices have exclusive open semantics.
2. **All hardware calls are serialized per device** through a `DeviceWorker` (single-thread executor). No exception.
3. **No pulse fires unless `ArmGate.require_armed()` succeeds.** This includes every code path in every router, the orchestrator, and any future feature.
4. **All pulse-emitting paths acquire a `RateLimiter` token.** Default 10/sec.
5. **The JSONL logbook is canonical.** The SQLite index is a derivable mirror, never the source of truth.
6. **State mutations broadcast.** Every change to `AppState` is followed by a `Broadcaster.broadcast()` call.

## Modules

### `safety.py` (seed)
`ArmGate` (hold-to-arm + auto-disarm timer), `RateLimiter` (sliding window), `StopFlag` (cooperative stop). Raise `Disarmed` / `RateLimited`. Carried forward from `old-em-setup/glitchweb/backend/app/safety.py`.

### `workers.py` (seed)
`DeviceWorker` wraps a `ThreadPoolExecutor(max_workers=1)` per device. `WorkerRegistry` holds one per device name. Carried forward from `old-em-setup/glitchweb/backend/app/workers.py`. Future split: separate read-queue from write-queue (status polls compete with writes today).

### `state.py` (seed)
`AppState` is the single in-memory snapshot: device statuses, position, counters, scan progress, arm state. `Broadcaster` distributes WS events with drop-oldest backpressure. Carry-forward from `old-em-setup/glitchweb/backend/app/state.py`.

### `logbook.py` (seed + new)
JSONL append-only writer carried from old code. **New**: a SQLite mirror updated on every append for the columns required by heatmap and replay queries.

### `orchestrator.py` (seed + extended)
`perform_attempt()` + `run_scan()` from old code. **Extended** with sweep dimensions (delay_us × pulse_width_ns × voltage_v) on top of the XYZ grid. Adds `replay(run_id)` that rehydrates an `AttemptResult` and re-executes the exact attempt.

### `ports.py` (seed)
VID/PID + manufacturer/serial-prefix matching. Carry-forward from `old-em-setup/glitchweb/backend/app/ports.py`.

### `config.py` (new)
JSON config under `~/.config/emfi-control/config.json` with hot reload. Schema mirrors `old-em-setup/glitchweb/backend/app/config.py` shape; auto-created on first start.

### `adapters/`
- `base.py` — common interface (`connect`, `disconnect`, `status`)
- `chipshover.py` — wraps `chipshover` pip package; XY logical↔machine coordinate transform
- `chipshouter.py` — wraps `chipshouter` pip package; idempotent arm/disarm, fault clearing
- `scaffold.py` — wraps `donjon-scaffold`; D0/D1/D2/D3 pin map, trigger-mode selector
- `xds110.py` — subprocess wrappers:
  - `flash(elf_path)` — invokes TI `dslite` or `uniflash` CLI; fast for the "build → flash → campaign" loop
  - `attach_debugger(elf_path)` — spawns OpenOCD on configured gdb/telnet ports for SW+HW combined attack analysis

## REST endpoints

```
GET    /devices                    list discovered serial devices
POST   /devices/{name}/connect     open serial port
POST   /devices/{name}/disconnect

POST   /motion/move_abs            { x, y, z } logical
POST   /motion/move_rel            { axis, distance }
POST   /motion/home
POST   /motion/set_origin
POST   /motion/set_top_right       { x, y }

POST   /shouter/arm
POST   /shouter/disarm
POST   /shouter/pulse              { voltage, pulse_width_ns, repeat }
POST   /shouter/config             { voltage, pulse_width_ns, mute, ... }

POST   /target/flash               { build_sha, elf_url }
POST   /target/reset
POST   /target/debug_attach        { build_sha, elf_url, gdb_port }

POST   /campaigns                  start a campaign (Campaign model)
GET    /campaigns                  list campaigns
GET    /campaigns/{id}             status + summary
POST   /campaigns/{id}/stop

GET    /runs?campaign=...&since=...&outcome=...&limit=...
GET    /runs/{id}
GET    /heatmap?campaign=...&z=...     fault density grouped by XY
POST   /replay/{run_id}            re-execute that exact attempt

POST   /arm
POST   /disarm
GET    /arm_state
```

All responses use Pydantic models from `emfi_protocol`. Error responses use FastAPI's default `{ "detail": "..." }`.

## WebSocket `/ws`

Server → client envelope: `emfi_protocol.WsEvent`.

Topics:
- `position` — `{ x, y, z, machine_x, machine_y, machine_z }`
- `arm` — `{ armed, seconds_until_auto_disarm }`
- `counter` — Counters snapshot
- `attempt` — `AttemptResult` (one per attempt completed)
- `device_status` — per-device `DeviceStatus`
- `campaign_progress` — `{ campaign_id, completed, total, current_xyz }`
- `state` — full `AppState.snapshot()` on connect
- `error` — `{ detail }`

Client → server actions (kept minimal; prefer REST for commands):
- `{ id, action: "subscribe", topics: [...] }` — optional topic filter
- `{ id, action: "ping" }`

## Storage layout

```
~/.local/share/emfi-control/
  sessions/
    logbook-YYYYMMDD.jsonl
    index.sqlite                  # mirror; schema below

~/.config/emfi-control/
  config.json
```

### SQLite schema (mirror)

```sql
CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  session TEXT NOT NULL,
  ts TEXT NOT NULL,
  campaign_id TEXT,
  x REAL, y REAL, z REAL,
  delay_us REAL, pulse_width_ns REAL, voltage_v INTEGER,
  outcome TEXT NOT NULL,
  build_sha TEXT,
  target_pc INTEGER
);
CREATE INDEX idx_runs_campaign ON runs(campaign_id);
CREATE INDEX idx_runs_outcome ON runs(outcome);
CREATE INDEX idx_runs_xy ON runs(x, y);
```

Mirror is updated on every `logbook.append()`. Full rebuild from JSONL is supported via `python -m control.tools.reindex`.

## Carry-forward bugs to fix

Documented in `old-em-setup/HANDOFF.md`. Highest priority during build-out:

- `Scaffold.bus.ser.close()` pokes internal attribute → use scaffold's public close.
- `chipshouter.wait_for_arm()` infinite block on HV failure → wrap with timeout + abort.
- Status polls share the worker queue with writes → split reader/writer queues per device.
- `sys.path` injection for adapters → replaced by this package's `adapters/` module.

## Testing

Pure-Python modules have unit tests with no hardware required:
- `tests/test_safety.py` — ArmGate states, auto-disarm timing, RateLimiter window
- `tests/test_workers.py` — single-threaded serialization, future propagation
- `tests/test_state.py` — counter math, snapshot stability
- `tests/test_logbook.py` — JSONL roundtrip, since/outcome filtering, SQLite index parity
- `tests/test_orchestrator.py` — fake adapters; exercise classification + grid sweep math

Hardware-touching tests are marked `@pytest.mark.hw` and skipped by default.
