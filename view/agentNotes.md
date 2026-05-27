# Agent Notes — View App

## What this app is

Pure SvelteKit static app (port 8003). No backend. Talks to Control (:8001) and Develop (:8002) over HTTP + WebSocket. It's the unified dashboard for the EMFI research rig — campaign control, live telemetry, heatmaps, assembly viewing, logbook.

## Current state (post-audit)

The scaffold is spec-complete. Every route, component, store, API client, and WS handler that SPEC.md commits to exists. Most components are stubs with TODO bodies — they have the right props/interfaces but don't render full UI yet.

### What was added in the audit pass

- `src/lib/stores/devices.ts` — was missing entirely from the scaffold
- `device_status` + `campaign_progress` WS topic handlers in `control_ws.ts`
- `devices()`, `getCampaign()`, `stopCampaign()` in `control.ts` API client
- Mission control page now uses ArmButton, DeviceStatusCard, LogTail components (was rendering inline)
- Layout now shows auto-disarm countdown + floating StopButton
- `src/lib/logger.ts` — structured client-side logging utility
- Logging wired into both API clients and both WS connections
- `start.sh` — startup script with log tee to `logs/` directory

### What still needs implementation (V1 scope)

1. **Scene3D.svelte** — Three.js scene init, positionStore subscription, click-to-jog raycasting
2. **Heatmap.svelte** — canvas rendering of `{x, y, count}[]` cells with color scale
3. **SweepConfig.svelte / GridConfig.svelte** — actual numeric input fields, validation against emfi_protocol shapes
4. **Campaign page** (`/campaign`) — project picker (Develop API), target picker, grid+sweep config, submit to Control
5. **Live campaign page** (`/campaign/[id]`) — progress bar, Scene3D, filtered LogTail
6. **Runs page** (`/runs`) — filter form, attempt table, replay button
7. **Assembly page** (`/assembly`) — project/build picker, Monaco-based assembly viewer, target click
8. **WS reconnect** — exponential backoff on disconnect (noted in TODOs)
9. **Active campaign store** — StopButton currently passes `'current'` as placeholder campaign ID

### Known limitations

- **openapi-typescript types not generated** — API clients are hand-rolled. The `protocol/openapi/*.yaml` files don't exist yet (they're generated from the running FastAPI apps). Once Control and Develop are running, generate types with the commands in SPEC.md.
- **No tests** — View is a pure frontend app; the spec doesn't call for tests. Consider Playwright e2e tests once the backends are up.
- **StopButton keyboard shortcut (Space)** — will interfere with normal typing in input fields on the campaign config page. Needs scoping so it only fires when no input is focused, or switch to a modifier combo.

## File map

```
view/
  start.sh                              # startup script (dev or preview mode)
  logs/                                 # server logs (gitignored, created by start.sh)
  package.json
  svelte.config.js                      # adapter-static, fallback to index.html
  vite.config.ts                        # proxy /control→:8001, /develop→:8002
  tsconfig.json
  src/
    app.html
    routes/
      +layout.svelte                    # nav, arm indicator + countdown, floating StopButton
      +page.svelte                      # mission control (ArmButton, position, counters, devices, log)
      campaign/+page.svelte             # campaign config form (stub)
      campaign/[id]/+page.svelte        # live campaign view (stub)
      runs/+page.svelte                 # logbook browser (stub)
      heatmap/+page.svelte              # 2D fault density (stub)
      assembly/+page.svelte             # assembly viewer (stub)
    lib/
      config.ts                         # CONTROL_URL, DEVELOP_URL, wsUrl()
      logger.ts                         # structured logging: createLogger(category)
      api/
        control.ts                      # 11 functions wrapping Control REST endpoints
        develop.ts                      # 5 functions wrapping Develop REST endpoints
      ws/
        control_ws.ts                   # always-on WS, dispatches 6 topics to stores
        develop_ws.ts                   # on-demand WS for build/agent streaming
      stores/
        arm.ts                          # { armed, auto_disarm_seconds, seconds_until_auto_disarm }
        position.ts                     # { x, y, z, machine_x?, machine_y?, machine_z? }
        counters.ts                     # { attempts, glitches, hangs, crashes, nothings, campaigns }
        devices.ts                      # Map<name, DeviceStatus>
        log.ts                          # AttemptEntry[] (capped at 200)
      components/
        ArmButton.svelte                # hold-to-arm (1000ms), touch+keyboard
        StopButton.svelte               # big red, Esc/Space global shortcut
        Scene3D.svelte                  # Three.js (stub)
        Heatmap.svelte                  # 2D canvas (stub)
        LogTail.svelte                  # append-only attempt list, outcome colors
        DeviceStatusCard.svelte         # per-device status card
        SweepConfig.svelte              # sweep range inputs (stub)
        GridConfig.svelte               # grid extent inputs (stub)
```

## How to run

```bash
# Dev (hot reload)
./start.sh dev

# Production preview
./start.sh preview

# Custom port
./start.sh dev 3000
```

Logs go to `logs/view-YYYYMMDD-HHMMSS.log` and are also printed to the terminal.

## Dependencies on other apps

- **Control (:8001)** — all runtime data. If Control is down, the WS won't connect and API calls will log network errors, but the app shell still renders.
- **Develop (:8002)** — project list, builds, disassembly. Only needed for `/campaign` and `/assembly` pages.
- **protocol/** — not a runtime dependency (View is pure JS). The protocol package defines the Pydantic models that generate the OpenAPI specs that would generate the TypeScript types.
