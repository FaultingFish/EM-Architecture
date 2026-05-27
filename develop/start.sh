#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# start.sh — Launch the EMFI Develop service
#
# Starts the FastAPI backend on port 8002.  All output is shown
# in the terminal AND appended to a timestamped log file under
# ./logs/ for post-mortem analysis.
#
# Usage:
#   ./start.sh              # default: INFO level, port 8002
#   ./start.sh --debug      # DEBUG level
#   ./start.sh --port 9002  # custom port
#
# Environment overrides (also respected by the Python code):
#   EMFI_LOG_LEVEL   INFO | DEBUG | WARNING  (default: INFO)
#   EMFI_LOG_DIR     path to log directory   (default: ./logs)
#   EMFI_PROJECTS_ROOT  path to projects     (default: ~/emfi-projects)
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Defaults ────────────────────────────────────────────────
PORT=8002
HOST="0.0.0.0"
LOG_LEVEL="${EMFI_LOG_LEVEL:-INFO}"
LOG_DIR="${EMFI_LOG_DIR:-$SCRIPT_DIR/logs}"
RELOAD=""

# ── Parse arguments ─────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)
            LOG_LEVEL="DEBUG"
            shift ;;
        --port)
            PORT="$2"
            shift 2 ;;
        --reload)
            RELOAD="--reload"
            shift ;;
        --help|-h)
            head -20 "$0" | grep '^#' | sed 's/^# \?//'
            exit 0 ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1 ;;
    esac
done

export EMFI_LOG_LEVEL="$LOG_LEVEL"
export EMFI_LOG_DIR="$LOG_DIR"

PROJECTS_PATH="${EMFI_PROJECTS_ROOT:-$HOME/emfi-projects}"

# ── Prepare log directory and session log file ──────────────
mkdir -p "$LOG_DIR"
SESSION_LOG="$LOG_DIR/develop-$(date +%Y%m%d-%H%M%S).log"

# Symlink logs/latest.log → the current session for easy access.
ln -sfn "$(basename "$SESSION_LOG")" "$LOG_DIR/latest.log"

# ── venv discovery / creation ───────────────────────────────
# Prefer (in order): caller-activated venv, local develop/.venv,
# shared ../.venv, then create develop/.venv as a last resort.
LOCAL_VENV="$SCRIPT_DIR/.venv"
SHARED_VENV="$SCRIPT_DIR/../.venv"

if [ -n "${VIRTUAL_ENV:-}" ]; then
    :
elif [ -d "$LOCAL_VENV" ]; then
    source "$LOCAL_VENV/bin/activate"
elif [ -d "$SHARED_VENV" ]; then
    source "$SHARED_VENV/bin/activate"
else
    echo "Creating virtual environment at $LOCAL_VENV ..."
    python3 -m venv "$LOCAL_VENV"
    source "$LOCAL_VENV/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet -e ../protocol -e ".[extras,dev]"
    echo "Virtual environment ready."
fi

# Ensure ~/.local/bin (Claude Code CLI) is on PATH for the agent endpoint.
export PATH="$HOME/.local/bin:$PATH"

# ── Banner ──────────────────────────────────────────────────
cat <<EOF

  EMFI Develop — starting up
  ──────────────────────────
  Port:       $PORT
  Log level:  $LOG_LEVEL
  Log file:   $SESSION_LOG
  Projects:   $PROJECTS_PATH
  venv:       ${VIRTUAL_ENV:-<none>}

  Ctrl-C to stop.

EOF

# ── Launch uvicorn, tee to both terminal and log file ───────
exec uvicorn develop.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')" \
    $RELOAD \
    2>&1 | tee -a "$SESSION_LOG"
