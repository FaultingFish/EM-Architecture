# EMFI Research Platform

A three-app architecture for electromagnetic fault injection (EMFI) research against the MSPM0L2228 target, running on a single lab computer over a trusted LAN.

## Apps

| App | Path | Port | Stack | Role |
|---|---|---|---|---|
| **Control** | [`control/`](./control/) | 8001 | FastAPI + WS | Owns hardware: ChipShover (XY), ChipSHOUTER (EMFI source), Scaffold (target IO), XDS110 (programmer). Singleton — one per rig. |
| **Develop** | [`develop/`](./develop/) | 8002 | FastAPI + SvelteKit | Firmware project management: C (TI HAL) + Rust (b01lers eCTF HAL). Builds, disassembly, glitch-target annotation, Claude Code agent generation. |
| **View** | [`view/`](./view/) | 8003 | SvelteKit (static) | Unified dashboard: campaign config, live 3D position, heatmap drill-down, assembly viewer, campaign notes/tags, logbook browser. |

Plus a shared `protocol/` package with Pydantic models + generated OpenAPI specs that both Python apps import and the SvelteKit apps consume as generated TypeScript types.

## Documentation map

| Doc | Read when |
|---|---|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | You want the system-design rationale and the carry-forward catalog |
| [`INSTALL.md`](./INSTALL.md) | You're standing up the platform on a fresh lab computer |
| [`setup.md`](./setup.md) | You're moving development to a new laptop |
| [`DOCS.md`](./DOCS.md) | You're running campaigns and need a usage / troubleshooting guide |
| [`docs/wiki/index.md`](./docs/wiki/index.md) | You want short runbooks for repeated operator/developer workflows |
| [`docs/remote-access.md`](./docs/remote-access.md) | You're exposing the lab through `emfi.ics.red` with Cloudflare Tunnel |
| [`docs/automation.md`](./docs/automation.md) | You're giving AI agents or scripts authenticated campaign access |
| [`agentsNotes.md`](./agentsNotes.md) | You're a Claude Code session picking up work on this repo |
| [`control/SPEC.md`](./control/SPEC.md), [`develop/SPEC.md`](./develop/SPEC.md), [`view/SPEC.md`](./view/SPEC.md) | You're building out one specific app |

## Quick start (after install)

Each app runs on the lab computer. From three terminals:

```bash
# Control (hardware singleton)
cd control && uvicorn control.main:app --host 0.0.0.0 --port 8001

# Develop (project + build service, bundled UI)
cd develop && uvicorn develop.main:app --host 0.0.0.0 --port 8002

# View (static SvelteKit)
cd view && npm run preview -- --host 0.0.0.0 --port 8003
```

Open `http://lab-box:8003/` in any browser on the LAN. For first-time setup follow [`INSTALL.md`](./INSTALL.md).

## Hardware

- ChipShover (XY stage, Smoothieware G-code)
- ChipSHOUTER (EMFI source, NewAE protocol)
- Ledger Donjon Scaffold (target IO + pulse gen)
- XDS110 (MSPM0 programmer / debugger)
- ChipWhisperer Husky (planned Platform crowbar path; Control has only a safe stub scaffold today)
- MSPM0L2228 (target MCU)

## Security model

The lab services are plain HTTP internally, but the public route is
`emfi.ics.red` through Cloudflare Tunnel and Cloudflare Access. Control and
Develop also support scoped app bearer tokens for automation. Do not expose
Control directly to the public internet.

## Heritage

`old-em-setup/` is the previous single-codebase implementation. It is the source of carry-forward patterns (safety primitives, per-device workers, JSONL logbook, campaign orchestrator). Do not modify it — it remains as a working reference and bug-history record.
