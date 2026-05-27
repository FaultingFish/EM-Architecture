# Agent Notes — Develop App

Notes from the audit and build-out sessions against the Develop scaffold.

## Session 1: Scaffold Audit (2026-05-26)

### What was audited
Walked through `SPEC.md` section-by-section, cross-referencing the plan file
(`i-am-looking-for-wiggly-quill.md`), `../ARCHITECTURE.md`, and every file in
`protocol/`.

### Gaps found and fixed

**[missing] — Git endpoints had no HTTP surface**
`git_ops.py` existed with `commit`, `tag`, `log` functions, but no router
exposed them. Created `routers/git.py` with:
- `POST /projects/{id}/git/commit`
- `POST /projects/{id}/git/tag`
- `GET  /projects/{id}/git/log`

**[missing] — `GET /templates` endpoint**
The spec lists a templates endpoint; no router existed.
Created `routers/templates.py`.

**[missing] — `frontend/src/lib/stores/` directory**
The plan file lists this directory in the scaffold tree but it was never
created. Added `stores/index.ts` placeholder.

**[drift] — Build trigger path was plural**
Spec says `POST /projects/{id}/build` (singular). Scaffold had
`POST /projects/{id}/builds` (plural, via router prefix). Fixed by removing
the prefix from the builds router and using explicit full paths so the
trigger is singular and list/get remain plural.

### Extra endpoints (kept, flagged)
`routers/artifacts.py` has `firmware.bin` and `firmware.lst` download
endpoints not in SPEC.md. These are useful since the build outputs include
those files. Recommend adding to spec or removing if strict spec compliance
is desired.

### Verification results
- `python3 -m py_compile` on all `.py` files: PASS
- `npx svelte-check`: PASS (0 errors, 0 warnings)
- Node.js installed via Volta; had to run `npx svelte-kit sync` first to
  generate `.svelte-kit/tsconfig.json`

---

## Session 2: Logging & start.sh (2026-05-26)

### Problem
Zero logging existed anywhere in the backend. No startup script.
Diagnosing runtime issues would require adding print statements after the
fact — not tenable for a lab service.

### What was added

**`backend/develop/logging_config.py`** — centralized setup:
- Configures root logger with both console (stdout) and rotating file handler
- File handler: 10 MB max, 5 backups, written to `./logs/develop.log`
- Env vars: `EMFI_LOG_LEVEL` (default INFO), `EMFI_LOG_DIR` (default `./logs`)
- Format: `timestamp | LEVEL | module | message`
- Quiets `uvicorn.access` to WARNING to avoid double-logging HTTP requests
  (we log them with timing in our own middleware instead)

**Request logging middleware** (`main.py`):
- Logs every HTTP request with method, path, status code, and elapsed time in ms
- Gives a single clean line per request for easy grep

**Lifecycle logging** (`main.py` lifespan):
- Logs on startup: log file path, projects root, templates root, frontend status
- Logs on shutdown

**Per-module loggers** — every backend module and router now has:
```python
import logging
log = logging.getLogger(__name__)
```
With appropriate log calls:
- `log.info` for state-changing operations (create, delete, build, commit, agent launch)
- `log.warning` for destructive operations (delete project, remove target)
- `log.debug` for read-only/frequent operations (list, get, tree)

**`start.sh`** — startup script:
- Starts uvicorn on port 8002 (configurable via `--port`)
- `--debug` flag sets log level to DEBUG
- `--reload` flag enables uvicorn hot-reload for development
- Creates timestamped session log: `logs/develop-YYYYMMDD-HHMMSS.log`
- Symlinks `logs/latest.log` to the current session
- Uses `tee` to display output in terminal AND save to file simultaneously
- Prints a startup banner with port, log level, log file path, projects root
- Respects `EMFI_LOG_LEVEL`, `EMFI_LOG_DIR`, `EMFI_PROJECTS_ROOT` env vars

### Log file locations
```
develop/
  logs/
    develop.log              # rotating file from Python's RotatingFileHandler
    develop-20260526-183000.log  # session log captured by start.sh via tee
    latest.log → develop-20260526-183000.log  # symlink to current session
```

Two complementary log sinks:
1. `develop.log` — the Python handler's rotating log, always active regardless
   of how the service is started (direct uvicorn, start.sh, etc.)
2. `develop-<timestamp>.log` — full stdout/stderr capture from start.sh,
   includes uvicorn's own output too

### Design decisions
- Used Python stdlib `logging` rather than structlog/loguru — zero new deps,
  matches the existing stack
- Rotating file handler rather than daily rotation — prevents a runaway build
  log from filling the disk
- Request timing in middleware rather than uvicorn access log — gives us
  control over format and lets us add request IDs later without changing
  uvicorn config
- Session log files are append-only and never deleted by the script — the
  user decides when to clean up

### What's left for build-out
When the `NotImplementedError` stubs are implemented, the log calls are already
in place. Future implementors should:
- Add `log.error(...)` in exception handlers when real error paths exist
- Add `log.info` for subprocess completion (build success/failure, agent exit code)
- Consider adding a request-ID header for correlating WS messages with the
  HTTP request that spawned them
