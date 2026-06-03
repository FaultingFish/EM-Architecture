# SETUP - moving development to a new laptop

This guide is for moving the developer workstation. The lab hardware stays on
`em-lab` (`stephen@faultierHost2`) and the checked-in repo stays the source of
truth for code changes.

For a fresh lab computer that owns the USB hardware, use [`INSTALL.md`](./INSTALL.md)
instead.

## 1. Install local prerequisites

On the new laptop:

- Git
- SSH client and your `em-lab` private key
- Python 3.11 or newer
- Node.js 20 or newer
- npm

Optional but useful:

- `uv` for faster Python environment creation
- `jq` for inspecting JSON responses and JSONL logs
- `ripgrep` (`rg`) for fast code search

## 2. Clone the repo

```bash
git clone git@github.com:FaultingFish/EM-Architecture.git
cd EM-Architecture
```

The current Mac checkout is named `EM-Architure`; the directory name is not
important. Keep the Git remote pointed at `FaultingFish/EM-Architecture`.

## 3. Restore SSH access to the lab

Copy or recreate the SSH key used for the lab box, then add an SSH config entry:

```sshconfig
Host em-lab
  HostName 10.164.9.112
  User stephen
  IdentityFile ~/.ssh/em_lab_box
```

Verify:

```bash
ssh em-lab 'hostname && cd ~/EM-Architecture && git status --short'
```

Do not store Cloudflare tunnel tokens, app bearer tokens, or private keys in the
repo. They live in the operator's password manager and on the lab host.

## 4. Create the local Python environment

The laptop does not need hardware libraries unless it will physically own the
rig. For normal development and tests:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e protocol -e 'control[dev]' -e 'develop[dev]'
```

Focused backend checks:

```bash
cd control
PYTHONPATH=src:../protocol ../.venv/bin/python -m pytest
cd ../develop
PYTHONPATH=src:../protocol ../.venv/bin/python -m pytest
```

## 5. Install View dependencies

```bash
cd view
npm install
npm run check
npm run build
```

Use `npm run dev -- --host 127.0.0.1 --port 5173` for local UI work. By
default, the production View talks to same-origin `/api/control` and
`/api/develop`; see [`docs/remote-access.md`](./docs/remote-access.md) for the
public tunnel layout.

## 6. Sync changes to the lab

Normal workflow:

```bash
# laptop
git status --short
git push

# lab
ssh em-lab 'cd ~/EM-Architecture && git pull --ff-only'
```

Control and Develop run with `uvicorn --reload` on the lab, so Python changes
usually reload after the pull. View is a static build and must be rebuilt and
copied into Caddy's web root:

```bash
ssh em-lab 'cd ~/EM-Architecture/view && npm install && npm run build && rm -rf /var/www/emfi-view/* && cp -a build/. /var/www/emfi-view/'
```

Check the public path:

```bash
curl -I https://emfi.ics.red/
```

Unauthenticated requests should hit Cloudflare Access. Authenticated browser
sessions should see View.

## 7. Files that are not in Git

These are intentionally machine-local:

| Item | Location |
|---|---|
| Control config | `~/.config/emfi-control/config.json` on `em-lab` |
| Control logbook and SQLite index | `~/.local/share/emfi-control/sessions/` on `em-lab` |
| Control audit JSONL | `~/.local/share/emfi-control/audit/` on `em-lab` |
| Last flashed DUT provenance | `~/.local/share/emfi-control/flashed_firmware.json` on `em-lab` |
| Campaign notes/tags | `~/.local/share/emfi-control/campaign_metadata.json` on `em-lab` |
| Develop projects and builds | `~/emfi-projects/` on `em-lab` |
| Cloudflare tunnel credentials | `cloudflared` service config on `em-lab` |
| App bearer tokens | environment/service config, not repo files |
| SSH keys | `~/.ssh/` |

Back up these paths before replacing the lab computer. For a laptop-only move,
only SSH keys and local editor/tool config need to move.

## 8. Migration validation checklist

- `ssh em-lab` works without typing a password.
- `git pull --ff-only` works on the lab checkout.
- Local `control` and `develop` test suites pass.
- `view/npm run check` and `view/npm run build` pass.
- `https://emfi.ics.red/` loads through Cloudflare Access.
- `https://emfi.ics.red/api/control/healthz` and
`https://emfi.ics.red/api/develop/healthz` return healthy responses after
  authentication.
- [`ROADMAP.md`](./ROADMAP.md) and [`docs/wiki/index.md`](./docs/wiki/index.md)
  are updated with any feature work done during the move.

## 9. AD2 dashboard capture notes

The dashboard scope panel can stream from a Digilent Analog Discovery 2 when the
lab computer owns the USB device. Install Digilent WaveForms on the lab host so
`libdwf.so` is present; Control uses that runtime directly through `ctypes`.

Current wiring convention:

| Dashboard trace | AD2 input | Rig signal |
|---|---|---|
| CH3 PULSE | Scope CH1 | ChipSHOUTER voltage monitor |
| CH2 TRIG | DIO0 | Ledger trigger/reference |
| CH1 CLK | DIO1 | Ledger-generated board clock |
| Optional markers | DIO2/DIO3 | Exposed status, UART, or firmware markers |

Control endpoints are `/devices/ad2/status`, `/devices/ad2/connect`,
`/devices/ad2/configure`, `/devices/ad2/capture`, `/devices/ad2/start_stream`,
and `/devices/ad2/stop_stream`. View auto-starts the stream when the dashboard
loads and falls back to the synthetic timing trace if the AD2 is not available.
The current ChipSHOUTER voltage-monitor lead is on a 20:1 probe, so Control
reports `pulse_probe_ratio: 20` and View renders CH3 as scaled pulse voltage
instead of auto-normalizing the noise floor.

For pulse validation, use `/devices/ad2/capture_triggered` or the dashboard
`TRIG` scope button. This arms a high-speed CH1 analog edge trigger at
100 MS/s, captures an 8192-sample window, and keeps DIO0/DIO1 samples aligned
with the pulse monitor. The default trigger level is `1.0 V` raw, which is
about `20 V` at the ChipSHOUTER monitor point through the 20:1 probe.

## 10. Bolted fixture profile

After homing, ChipShover clears the logical origin. For the bolted-down board,
save the calibrated chip scan box as the default fixture from the calibration
page. Control persists it in `~/.config/emfi-control/config.json` under
`fixture.default_grid`, including both logical grid bounds and the machine-space
origin. The campaign page can then apply the fixture after a home, restoring the
chip corner as logical `(0, 0, 0)` without manually jogging the probe.

Useful endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /motion/fixture` | Read the saved default fixture |
| `POST /motion/fixture/save_current` | Save the current origin/top-right as the default fixture |
| `POST /motion/fixture/apply` | Restore the saved machine origin and grid after homing |
