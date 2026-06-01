# ROADMAP

Living checklist of features for the EMFI research platform. Sessions check items off as they ship. When you complete a feature, tick its box in the same commit that lands the work.

Three tiers:
- **V1 must-haves** — without these the campaign loop doesn't actually run end-to-end.
- **V1+ nice-to-haves** — what turns "works" into "a tool you enjoy".
- **Phase 2** — deferred by explicit decision in `ARCHITECTURE.md`. Don't pull these forward without asking.

Each item names the owning app(s) and a short description. Cross-app items list both.

---

## V1 must-haves

- [ ] **Orchestrator port** — `Orchestrator.perform_attempt` + `run_campaign` from `old-em-setup/glitchweb/backend/app/orchestrator.py`, extended with `delay_us × pulse_width_ns × voltage_v` sweep on top of the XYZ grid. Host-script invocation via `importlib.spec_from_file_location`. **(control)**
- [ ] **Live campaign telemetry** — orchestrator publishes WS events: `position`, `attempt`, `counter`, `campaign_progress`. **(control)** — rolled into orchestrator
- [ ] **STOP works mid-campaign** — `StopFlag` checked between every attempt; STOP / Esc / Space cleanly interrupts the running campaign. **(control)** — rolled into orchestrator
- [ ] **Replay mode** — `POST /replay/{run_id}` re-runs the attempt with the exact recorded parameters. **(control)** — rolled into orchestrator
- [ ] **dslite syntax fix** — flash actually programs the chip; current invocation makes dslite print --help. **(control)**

## V1+ nice-to-haves

- [x] **Calibration wizard** — 3-step UI flow: origin → top-right → confirm with 3D preview. **(view)**
- [x] **Hardware status panel** — always-visible header strip with device states + ChipSHOUTER voltage/faults. **(view)**
- [ ] **Pre-flight checklist** — campaign-start gate verifying all devices connected, firmware flashed matches build_sha, voltage in safety bounds, ARM gate behavior. **(control endpoint + view UI)**
  - [x] control: preflight endpoint for device, voltage, ARM-state, grid, and pulse-budget checks
  - [x] view: pre-submit grid/sweep estimate + small-grid warning on campaign form; calibration wizard blocks `top_right == origin`
  - [ ] control: verify flashed firmware/build provenance against `build_sha`
- [x] **Time + cost estimator** — display total pulse count + ETA on the campaign config form before submit. **(view, reads stats from existing endpoints)**
- [ ] **Campaign presets** — save/reload named campaign configurations per project. **(develop storage + view picker)**
  - [x] develop: storage + REST endpoints
  - [ ] view: picker on campaign config form
- [ ] **GlitchTarget range** — `pc_end` field so a single target spans an instruction range; campaign sweeps delay across the range. **(develop protocol + view picker)**
  - [x] develop: protocol fields + storage round-trip
  - [ ] view: range-select in AssemblyView
- [x] **Hardware-triggered pulse via Scaffold pgen** — D0 rising edge → pgen0 (programmable delay) → A0 ChipSHOUTER trigger, all in hardware (zero USB jitter). `trigger_mode="one-shot"` wires `d0 → pgen0.start`, `pgen0.out → a0`; sweep delay/width set per attempt via `pgen0.delay`/`pgen0.width`. **(control)**
- [ ] **Stop conditions** — "stop after N glitches", "stop on first crash", "stop after X minutes". **(control orchestrator + view UI)**
- [ ] **Heatmap drill-down** — click a hot cell → see the attempts that produced glitches, with delay/voltage/pulse-width/target-PC for each. **(view, reads existing /runs)**
- [ ] **Heatmap parameter histogram** — `(delay_us, pulse_width_ns)` joint distribution for cells with ≥N glitches; finds sweet spots. **(view)**
- [ ] **Campaign notes + tags** — free-text + tag per campaign; filter in the runs browser. **(control storage + view UI)**
- [ ] **CSV / Parquet export** — `GET /runs/export?format=csv|parquet&campaign=…`. **(control)**
- [ ] **State snapshot / restore** — capture the full rig configuration (ChipSHOUTER settings, position, ARM state) and restore later. **(control)**
- [ ] **Pause / resume mid-campaign** — graceful pause that keeps position + counters, plus resume. **(control + view buttons)**
- [ ] **Multi-project comparison** — heatmaps for two campaigns/projects side-by-side or overlaid. **(view)**
- [ ] **Auto-resume after ChipSHOUTER fault** — clear fault and continue the campaign (configurable per-campaign). **(control orchestrator)**

## Remote ops + automation

- [x] **Single public origin plan** — document `emfi.ics.red` as one Cloudflare Access-protected hostname with local path routing to View, Control, and Develop. **(ops/docs)**
- [x] **Local reverse-proxy examples** — add localhost-only Caddy routing for `/`, `/api/control`, and `/api/develop`. **(ops)**
- [x] **Systemd service examples** — add service templates for Control, Develop, View, and Caddy bound to `127.0.0.1`. **(ops)**
- [x] **Cloudflare Tunnel example** — add a locally-managed `cloudflared` config with a deny-by-default ingress fallback. **(ops)**
- [x] **Health/readiness endpoints** — add `/healthz` and `/readyz` for Control and Develop. **(control + develop)**
- [x] **Same-origin View defaults** — make View default to `/api/control` and `/api/develop`, including WebSocket URL generation. **(view)**
- [x] **Application auth middleware** — add scoped bearer-token auth on top of Cloudflare Access service tokens. **(control + develop)**
- [ ] **Automation preflight endpoint** — validate devices, rails, build provenance, grid bounds, pulse budget, and safety limits before agent-launched campaigns. **(control + view)**
  - [x] initial endpoint + view gate for device, rail, grid, pulse-budget, and safety checks
  - [ ] flashed-firmware provenance and stop-condition policy checks
- [ ] **Audit log for dangerous actions** — append operator/agent identity and request metadata for arm, pulse, motion, power, flash, and campaign start/stop. **(control)**
- [ ] **Dual-target campaign model** — represent DUT EMFI plus platform voltage-glitch timing explicitly for ChipWhisperer Husky/crowbar experiments. **(protocol + control + view)**

## Phase 2 (deferred)

- [ ] **USB webcam overlay + click-to-jog calibration** — visible bed → click → jog. **(control + view)**
- [ ] **Cross-rig comparison** — heatmap diff across multiple lab boxes. **(control + view)**
- [ ] **Cloud archive of logbooks** — nightly S3 / Azure Blob backup of JSONL sessions. **(control + ops)**
- [ ] **OpenOCD PC trace at glitch moment** — capture target PC at attempt time for forensic analysis. **(control)**
- [ ] **Bisect mode** — auto-narrow on hot regions across successive campaigns. **(control + view)**
- [ ] **Persistent ARM mode** — disable auto-disarm for hands-off long-running campaigns. **(control safety)**
- [ ] **Delta-encoded WS state broadcasts** — send diffs instead of full snapshots. **(control)**
- [ ] **Continuous heartbeat watcher** — background coroutine, not just inter-attempt polling. **(control)**

---

## Convention

When you complete an item:
1. Check the box `[x]` in the same commit that lands the feature.
2. If a single item splits into multiple sub-tasks (e.g. the orchestrator port covers four V1 must-haves), tick all that the commit completes.
3. Don't add items here unilaterally — propose new features in `agentConversation.md` first; once the human accepts, add to ROADMAP.
