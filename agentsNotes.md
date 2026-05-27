# agentsNotes.md — notes for Claude / agent sessions

If you are a Claude Code (or similar) session opened in this repo, read this first. It's the working memory of prior sessions: what was decided, what is intentional, what to avoid touching, and how this repo expects you to operate.

## 1. What this repo is

A three-app monorepo for EMFI (electromagnetic fault injection) research against the MSPM0L2228 target. Apps:

- `control/` — FastAPI service that owns the singleton hardware (ChipShover, ChipSHOUTER, Scaffold, XDS110). Port 8001.
- `develop/` — FastAPI + bundled SvelteKit for firmware project management, builds, disassembly, glitch-target annotation, and a Claude Code agent endpoint. Port 8002.
- `view/` — Static SvelteKit dashboard. Port 8003.
- `protocol/` — Shared Pydantic models (`emfi-protocol` package) — single source of truth for the wire format.
- `old-em-setup/` — Reference implementation. **Do not edit.** Source of the carry-forward modules in Control.

## 2. Definitive documents (in priority order)

Read these before you do anything substantive. When they disagree, the higher-priority one wins:

1. **The plan file**: `/Users/sglombic/.claude/plans/i-am-looking-for-wiggly-quill.md` — the authoritative architecture plan and scope.
2. **`ARCHITECTURE.md`** — system design, rationale, carry-forward catalog.
3. **`<app>/SPEC.md`** — the contract for that specific app.
4. **`<app>/setup.md`** — deployment-specific facts (lab box, pinned device paths, library quirks). Read this if you're touching anything that runs on the real rig.
5. **`agentConversation.md`** (repo root) — shared inter-session channel. Scan it at the start of every session for messages addressed to your app.
6. **`old-em-setup/HANDOFF.md`** — bug history. The fixes in this file are why the new code looks the way it does. If you find yourself "improving" a piece of carry-forward code, check this first.

User-facing docs (you don't usually maintain these unless asked): `README.md`, `INSTALL.md`, `DOCS.md`.

## 3. Carry-forward — do not rewrite

These modules in `control/src/control/` are intentional verbatim ports from `old-em-setup/glitchweb/backend/app/`. They survived real lab incidents. Leave them alone unless explicitly asked.

- `safety.py` — ArmGate / RateLimiter / StopFlag.
- `workers.py` — DeviceWorker single-thread executor per device.
- `state.py` — AppState + Broadcaster.
- `logbook.py` — JSONL append-only log (extended with SQLite mirror; the mirror logic IS new and editable).
- `ports.py` — VID/PID-based device classification.

The carry-forward bugs to avoid re-introducing live in `old-em-setup/HANDOFF.md`. Key ones:
- Idempotent `ChipShouterAdapter.arm()` (don't double-arm the upstream lib).
- `ChipShouterAdapter.arm()` must time out when HV stalls.
- Use the Scaffold lib's public close, not `bus.ser.close()`.
- Trigger mode is a *user-selectable* `software | one-shot | free-run | disabled`. Don't simplify it away.

## 4. Scope rules — what to NOT do

The user has been explicit and consistent on these:

- **Don't add features beyond what `SPEC.md` and the plan file commit to.** If you see a "would be nice" idea, file it; don't build it.
- **Don't add Phase-2 features**: USB webcam overlay, continuous heartbeat watcher, delta-encoded WS, cross-rig comparison, cloud backup, agent loops that span apps.
- **Don't add auth, TLS, or rate-limiting on the HTTP layer.** Deployment is trusted LAN. Stated user requirement.
- **Don't refactor passing tests** unless you broke them or the spec changed.
- **Don't create new top-level markdown files** unless the user asks. The current set is: `README.md`, `ARCHITECTURE.md`, `INSTALL.md`, `DOCS.md`, `agentsNotes.md`. Per-app: `README.md`, `SPEC.md`, and an `AUDIT.md` from the initial audit pass.
- **Don't modify `old-em-setup/`.** It's read-only history.
- **Don't modify the plan file.** It's locked-in design.

## 5. Patterns to preserve

If you're adding new code, match these patterns. They're non-obvious but load-bearing.

- **Every hardware call goes through a `DeviceWorker`.** Even reads. No exceptions, no "just this once". This is what makes pyserial concurrency safe with multiple browser tabs.
- **Every pulse-emitting code path calls `arm_gate.require_armed()` and `rate_limiter.acquire()`** before talking to the SHOUTER. Including future endpoints, replay, anything new. If you forget, you've built a safety regression.
- **JSONL is canonical.** SQLite is a mirror. New columns? Add to BOTH and ship a reindex command.
- **Errors carry context.** Use `_format_error()` style prefixes so journalctl + the UI toast both make sense. Empty exception messages were a documented HANDOFF pain point.
- **Broadcaster drops on backpressure, never blocks.** Producers should not stall because one slow WS client filled its queue.
- **Pydantic v2 only.** Both Python apps use it. Don't reach for dataclasses on the wire — every wire type goes in `protocol/`.

## 6. Repo layout

```
.
├── README.md               # orientation
├── ARCHITECTURE.md         # design rationale
├── INSTALL.md              # deploy guide
├── DOCS.md                 # operator + troubleshooting guide
├── agentsNotes.md          # this file
├── .gitignore
│
├── protocol/               # emfi-protocol (Pydantic models, OpenAPI)
├── control/                # FastAPI hardware service (:8001)
│   ├── SPEC.md
│   ├── src/control/{adapters,routers,tools}/
│   └── tests/              # safety/workers/state/logbook are seeded; orchestrator skipped
├── develop/                # FastAPI + SvelteKit (:8002)
│   ├── SPEC.md
│   ├── AUDIT.md            # initial audit report (read for context)
│   ├── backend/develop/{routers,templates}/
│   ├── frontend/           # SvelteKit, served as static via FastAPI in prod
│   └── tests/
├── view/                   # SvelteKit static (:8003)
│   ├── SPEC.md
│   ├── AUDIT.md            # initial audit report
│   └── src/{routes,lib}/
└── old-em-setup/           # READ-ONLY reference (prior implementation)
```

Per-app `AUDIT.md` files list what was [present]/[missing]/[drift]/[extra] vs SPEC.md after the scaffold pass. Useful to know what's been triaged already.

## 7. Working in a single-app session

When the user opens you in `control/` (or `develop/`, or `view/`), they expect you to:

- Treat that folder as your working tree. Don't reach into the others unless you have a specific reason and they OK'd it.
- Read `./SPEC.md` first thing.
- Use the carry-forward source paths in `old-em-setup/` for reference, never as targets to modify.
- Stage your work against the existing scaffold style — stubs with `raise HTTPException(status_code=501, detail="TODO")`, models that import from `emfi_protocol`, tests that mark hardware-dependent cases as `@pytest.mark.hw` and skipped by default.

## 8. The standing audit prompt

There is a standing prompt the user feeds into each app's session for periodic audits. If you are invoked with text matching that prompt, follow it: produce an audit report first, then fix what's safely within V1 scope, then summarize. The prompt's exact content was given in the architecture discussion — the user keeps it; ask for it if you need it again.

## 9. Useful one-liners

```bash
# Syntax-check every Python file
python -m py_compile $(find . -name "*.py" -not -path "*/old-em-setup/*" -not -path "*/.venv/*")

# Type-check a SvelteKit app
cd view && npx svelte-check
cd develop/frontend && npx svelte-check

# Regenerate OpenAPI specs for typed TS clients
python -c "from control.main import app; import json,sys; json.dump(app.openapi(), sys.stdout)" \
  > protocol/openapi/control.json
python -c "from develop.main import app; import json,sys; json.dump(app.openapi(), sys.stdout)" \
  > protocol/openapi/develop.json

# Tail Control's logbook
tail -F ~/.local/share/emfi-control/sessions/logbook-$(date -u +%Y%m%d).jsonl
```

## 10. When in doubt

Ask. The user prefers a clarifying question to a confident guess that introduces scope creep or a safety regression. The cost of asking is small; the cost of, say, removing the ArmGate "to simplify" is large.
