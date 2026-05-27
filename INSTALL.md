# INSTALL — bring up the EMFI platform on a fresh lab computer

This document gets you from a clean Ubuntu/Debian box to all three apps running and the rig responding. Tested mental model: Ubuntu 22.04+. Other distros work; substitute the package manager.

> Everything in this guide runs **on the lab computer itself** — the singleton hardware lives there. No part of this should be deployed to a public host.

---

## 0. Prerequisites — what you need before you start

- A Linux machine (the "lab box") with USB and a static LAN IP.
- USB devices plugged in: ChipShover, ChipSHOUTER, Scaffold, XDS110.
- Network: a trusted lab LAN. The lab box exposes ports 8001/8002/8003 to it.
- An account on the lab box with `sudo` for package installs. After install, the services can run as your normal user — they only need access to the serial device nodes.

---

## 1. System packages

```bash
sudo apt update
sudo apt install -y \
  python3.11 python3.11-venv python3-pip \
  build-essential pkg-config git curl \
  gcc-arm-none-eabi binutils-arm-none-eabi gdb-multiarch \
  openocd \
  nodejs npm
```

If your distro ships Node < 18, install via NodeSource or `fnm`. SvelteKit needs Node 18+.

### Rust toolchain (for the b01lers HAL target)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustup target add thumbv8m.main-none-eabi
```

### TI UniFlash / `dslite` (XDS110 production flashing)

Download UniFlash for Linux from <https://www.ti.com/tool/UNIFLASH> and install to `/opt/ti/uniflash` (or wherever you like). The CLI binary is typically at:
```
/opt/ti/uniflash/dslite.sh
```
You'll set `DSLITE_BIN` in Control's config to this path.

### Claude Code CLI (for Develop's agent endpoint)

```bash
# Install per upstream docs at https://docs.claude.com/en/docs/claude-code
# The Develop service shells out to `claude` on PATH.
claude --version
```

If the lab box is air-gapped from Anthropic's API, the agent endpoint will return errors at runtime — that's expected; the rest of Develop continues to work.

---

## 2. Serial device access

The Control service opens USB serial ports directly. Without `dialout` access, every connect will fail with `PermissionError`.

```bash
sudo usermod -aG dialout $USER
sudo usermod -aG plugdev $USER   # XDS110 typically also needs this
# Log out and back in for group changes to take effect.
```

Verify each device shows up:
```bash
ls -l /dev/ttyUSB* /dev/ttyACM*  # ChipShover/ChipSHOUTER/Scaffold
lsusb | grep -i 'XDS110\|Texas Instruments'
```

If devices keep changing paths between reboots, add udev rules. Control identifies devices by **VID/PID + manufacturer/serial-prefix**, not by path, so paths drifting is OK — Control will rediscover. But pinning paths makes debugging easier:

```bash
# /etc/udev/rules.d/99-emfi.rules — examples; pull real VIDs from `lsusb -v`
SUBSYSTEM=="tty", ATTRS{manufacturer}=="Smoothie", SYMLINK+="ttyShover"
SUBSYSTEM=="tty", ATTRS{manufacturer}=="NewAE", SYMLINK+="ttyShouter"
SUBSYSTEM=="tty", ATTRS{manufacturer}=="FTDI", ATTRS{serial}=="scaffold*", SYMLINK+="ttyScaffold"
```

Reload: `sudo udevadm control --reload && sudo udevadm trigger`.

---

## 3. Get the code

```bash
git clone <your-internal-git-url>/EM-Architure.git ~/EM-Architure
cd ~/EM-Architure
```

(If you don't yet have a git remote, `git init` here and commit; the apps don't require a remote.)

---

## 4. Python apps — protocol, Control, Develop

```bash
cd ~/EM-Architure

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Shared models first
pip install -e protocol/

# Control + its hardware deps
pip install -e 'control/[hw,dev]'

# Develop + extras
pip install -e 'develop/[extras,dev]'
```

The `[hw]` extra installs `chipshover`, `chipshouter`, and `donjon-scaffold`. The `[dev]` extras install pytest + httpx.

### Smoke tests

```bash
# Protocol imports
python -c "from emfi_protocol import Campaign, AttemptResult; print('protocol OK')"

# Control unit tests (no hardware required)
cd control && pytest -q && cd ..

# Develop unit tests (skips most; runs what's implemented)
cd develop && pytest -q && cd ..
```

You should see test_safety / test_workers / test_state / test_logbook pass on Control.

---

## 5. View — frontend builds

```bash
cd ~/EM-Architure/view
npm install
npm run check         # type check
npm run build         # produce static build under ./build/
cd ..
```

Develop's bundled UI:
```bash
cd ~/EM-Architure/develop/frontend
npm install
npm run build         # static build mounted by Develop's FastAPI app
cd ../..
```

---

## 6. Configuration

### Control

On first run Control writes `~/.config/emfi-control/config.json` with safe defaults. Edit it to set:

- `programmer.dslite_bin` — path to `dslite.sh` from your UniFlash install
- `programmer.openocd_bin` — path to `openocd` (usually `/usr/bin/openocd`)
- `programmer.openocd_config` — OpenOCD config file for XDS110 + MSPM0L2228
- `ports.*_override` — only if you want to pin specific `/dev/tty*` paths
- `safety.max_voltage_v` — clamp for the SHOUTER

A `.env` next to `control/pyproject.toml` can override host/port and the Develop URL. See `control/.env.example`.

### Develop

Environment variables (optional; defaults are sensible):
- `EMFI_PROJECTS_ROOT` — defaults to `~/emfi-projects/`
- `CLAUDE_BIN` — defaults to `claude` on PATH
- `ARM_GCC_BIN`, `ARM_OBJDUMP_BIN`, `CARGO_BIN` — defaults from PATH

### View

Service URLs are baked at build time from `view/src/lib/config.ts`. To point View at a different host, set Vite env vars before `npm run build`:

```bash
VITE_CONTROL_URL=http://lab-box:8001 \
VITE_DEVELOP_URL=http://lab-box:8002 \
npm run build
```

---

## 7. Running the services

### Quick (foreground, three terminals or a `tmux` session)

```bash
# T1
cd ~/EM-Architure && source .venv/bin/activate
cd control && uvicorn control.main:app --host 0.0.0.0 --port 8001

# T2
cd ~/EM-Architure && source .venv/bin/activate
cd develop && uvicorn develop.main:app --host 0.0.0.0 --port 8002

# T3
cd ~/EM-Architure/view && npm run preview -- --host 0.0.0.0 --port 8003
```

### Production (systemd)

Drop these unit files into `/etc/systemd/system/`:

**`emfi-control.service`**
```ini
[Unit]
Description=EMFI Control
After=network.target

[Service]
User=lab
WorkingDirectory=/home/lab/EM-Architure/control
Environment="PATH=/home/lab/EM-Architure/.venv/bin"
ExecStart=/home/lab/EM-Architure/.venv/bin/uvicorn control.main:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

**`emfi-develop.service`** — same shape, swap `control`→`develop`, port `8002`.

**`emfi-view.service`**
```ini
[Unit]
Description=EMFI View
After=network.target

[Service]
User=lab
WorkingDirectory=/home/lab/EM-Architure/view
ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 8003
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now emfi-control emfi-develop emfi-view
sudo systemctl status emfi-control
```

Tail logs with `journalctl -u emfi-control -f`.

---

## 8. Firewall

If `ufw` is active, allow only LAN traffic:
```bash
sudo ufw allow from 10.0.0.0/24 to any port 8001
sudo ufw allow from 10.0.0.0/24 to any port 8002
sudo ufw allow from 10.0.0.0/24 to any port 8003
```
Replace `10.0.0.0/24` with your lab subnet. **Do not expose these ports outside the lab LAN** — there is no auth.

---

## 9. Verify end to end

1. `curl http://lab-box:8001/docs` — Swagger UI for Control loads
2. `curl http://lab-box:8002/docs` — Swagger UI for Develop loads
3. `http://lab-box:8003/` in a browser — View renders the mission control page; the header arm indicator flips from `safe` ↔ `ARMED` if you click hold-to-arm (only after you implement the arm endpoint — V1 scaffold may still return 501)
4. With the rig powered on and devices connected: `GET /devices` on Control returns four entries with `connected: true`

If any of these fail, jump to [`DOCS.md`](./DOCS.md) for troubleshooting.

---

## 10. Updating

```bash
cd ~/EM-Architure
git pull
source .venv/bin/activate
pip install -e protocol/ -e 'control/[hw,dev]' -e 'develop/[extras,dev]'
cd view && npm install && npm run build && cd ..
cd develop/frontend && npm install && npm run build && cd ../..
sudo systemctl restart emfi-control emfi-develop emfi-view
```

When the OpenAPI surface of Control or Develop changes, regenerate the typed clients:
```bash
# from view/
npx openapi-typescript ../protocol/openapi/control.yaml -o src/lib/api/control.types.ts
npx openapi-typescript ../protocol/openapi/develop.yaml -o src/lib/api/develop.types.ts
```
