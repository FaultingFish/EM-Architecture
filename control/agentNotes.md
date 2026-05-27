# Control App — Agent Notes

Notes from the audit and build-out sessions on this app.

---

## Audit Summary (Session 1)

Walked SPEC.md section-by-section against the scaffold. State before fixes:

### What was present and correct
- All 8 spec'd REST endpoint groups exist as router stubs (devices, motion, shouter, target, campaigns, runs, safety, ws).
- All 5 seed modules (safety, workers, state, logbook, ports) are faithful ports of the old carry-forward code.
- Orchestrator stub has correct signatures for `perform_attempt`, `run_campaign`, `replay`.
- All 4 HANDOFF.md carry-forward bugs are addressed or documented at the correct location:
  - `Scaffold.bus.ser.close()` fragile → TODO in `adapters/scaffold.py`
  - `wait_for_arm()` infinite block → timeout parameter in `adapters/chipshouter.py`
  - `arm()` idempotent → docstring + signature in `adapters/chipshouter.py`
  - `sys.path` injection → replaced by `control.adapters` package
- SQLite schema in `logbook.py` matches SPEC.md exactly.
- All 5 test files present; 21 pass, 4 skipped (orchestrator stubs).
- pyproject.toml declares all required deps.
- Protocol models (`emfi_protocol`) match what the routers import.

### What was missing and added
| Item | Fix |
|------|-----|
| `control.tools.reindex` — SPEC says `python -m control.tools.reindex` for SQLite rebuild | Created `src/control/tools/{__init__,__main__,reindex}.py` |

### What had drift and was resolved
| Item | Drift | Fix |
|------|-------|-----|
| `config.py` | SPEC says "hot reload" + "mirrors old config shape"; scaffold had bare `load()`/`save()` functions | Rewrote as `Config` class with `load`, `save`, `snapshot`, `update`, `get` — matching old carry-forward |
| `adapters/base.py` | SPEC says common interface is `(connect, disconnect, status)`; scaffold only had `connected` property | Added `status()` method returning `{name, connected, port, last_error}` |

### Flagged for user
- `POST /target/debug_detach` exists in `routers/target.py` but is not in SPEC.md. It is functionally needed to stop the OpenOCD process started by `debug_attach`. Consider adding to SPEC.md.

---

## Logging & Startup (Session 2)

### Problem
The scaffold had almost zero logging infrastructure:
- Only `orchestrator.py` and `workers.py` created a `LOGGER`.
- No log configuration — no format, no file handler, no rotating logs.
- No `start.sh` or any startup script.
- The old codebase (`old-em-setup/glitchweb/`) had proper logging to both console and a rotating file at `~/.local/state/glitchweb/logs/server.log` with 5MB×5 backups.

### What was added

**Logging configuration** (`main.py`):
- `setup_logging()` configures the root logger with both a `StreamHandler` (console) and a `RotatingFileHandler` (file).
- Log file: `~/.local/share/emfi-control/logs/control.log` (10MB × 5 backups).
- Overridable via `CONTROL_LOG_DIR` env var.
- Format: `2026-05-26 14:30:00 INFO     control.safety: ARM gate ENGAGED`
- Uvicorn access log demoted to WARNING to reduce noise.
- HTTP request/response middleware logs all requests and warns on 4xx/5xx.
- Runs as part of FastAPI lifespan — logging is configured before the first request.

**Per-module loggers added** to every module that was missing one:
- `safety.py` — logs arm/disarm transitions, auto-disarm events, blocked pulses, rate-limit hits
- `state.py` — logs WS client register/unregister
- `logbook.py` — logs session open, append operations, listener errors
- `config.py` — logs config load/create, parse failures
- `ports.py` — logs port scan results
- `adapters/chipshover.py`, `chipshouter.py`, `scaffold.py`, `xds110.py` — logger ready for build-out
- `routers/ws.py` — logs WS connect/disconnect with client address

**`start.sh`**:
- Creates/activates a `.venv` automatically on first run.
- Installs `../protocol` and the control package with dev deps.
- Supports `--reload` (for dev) and `--debug` (DEBUG-level logging).
- Prints a startup banner with service URL, log file path, and PID.
- Exports `CONTROL_HOST`, `CONTROL_PORT`, `CONTROL_LOG_DIR` for `main.py`.
- Uses `exec` so the uvicorn process replaces the shell (clean signal handling).

### Log locations
```
~/.local/share/emfi-control/logs/control.log      # rotating server log (10MB × 5)
~/.local/share/emfi-control/sessions/              # JSONL logbook (canonical data)
~/.config/emfi-control/config.json                 # persistent config
```

---

## Architecture Notes

### What still needs build-out (V1 scope, stubs exist)
These are all `raise NotImplementedError` stubs that the build-out session should fill in:

1. **Orchestrator** — `perform_attempt()`, `run_campaign()`, `replay()`. Reference: `old-em-setup/glitchweb/backend/app/orchestrator.py` lines 49-222.
2. **All adapter `.connect()` / `.disconnect()` methods** — each wraps the upstream pip library.
3. **All router endpoint bodies** — currently return 501. Wire them to adapters + state + logbook.
4. **WS router** — needs to bind to `Broadcaster`, send initial state snapshot, handle `subscribe`/`ping`.

### What is Phase 2 (deferred, do NOT implement)
- USB webcam overlay + optical calibration
- Continuous background heartbeat watcher coroutine
- Delta-encoded WS state broadcasts
- Cross-rig comparison / cloud archive
- AWS S3 / Azure Blob nightly logbook backup

### Key invariants to preserve
1. All hardware calls go through `DeviceWorker` (single-thread-per-device executor).
2. All pulse-emitting paths call `arm_gate.require_armed()` then `rate_limiter.acquire()`.
3. JSONL logbook is canonical; SQLite is a rebuildable mirror.
4. State mutations broadcast via `Broadcaster`.
5. One process per rig (serial devices have exclusive open semantics).

### Test strategy
- Pure-Python modules tested without hardware: safety, workers, state, logbook.
- Orchestrator tests use fake adapters (in-memory, no hardware).
- Hardware tests marked `@pytest.mark.hw`, skipped by default.
- Run all: `pytest tests/` (from the control/ dir or via `start.sh` with the venv active).

### Environment
- Python 3.11+ required (tested on 3.14.4).
- pyproject.toml uses `src/` layout — `control` package lives at `src/control/`.
- Protocol installed as editable dep: `pip install -e ../protocol`.
