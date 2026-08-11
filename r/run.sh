#!/bin/bash
set -e

# Change to the script's directory regardless of where it was called from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Locate system Python or install via apt if missing
if command -v python3 &>/dev/null; then
    SYS_PYTHON="python3"
elif command -v python &>/dev/null; then
    SYS_PYTHON="python"
else
    echo "[!] Python 3 not found on system."
    if command -v apt-get &>/dev/null; then
        echo "[*] Installing Python 3 via apt-get..."
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
        SYS_PYTHON="python3"
    else
        echo "[ERROR] Python 3 is required but not installed."
        exit 1
    fi
fi

# Determine default port from port.ini or positional argument
INI_PORT=$($SYS_PYTHON -c "from port_config import get_configured_port; print(get_configured_port())" 2>/dev/null || echo "3000")
PORT="${1:-$INI_PORT}"

echo "=================================================="
echo "   HOMELAB GNOME DASHBOARD - PORTABLE RUNNER"
echo "=================================================="
echo ""

# Run dependency bootstrapper (installs pip / apt packages automatically)
$SYS_PYTHON bootstrap.py

VENV_PYTHON=".venv/bin/python"
if [ -f "$VENV_PYTHON" ]; then
    RUNNER="$VENV_PYTHON"
else
    RUNNER="$SYS_PYTHON"
fi

mkdir -p static/wallpapers

echo ""
echo "[OK] Starting Homelab Dashboard on http://localhost:$PORT (configured in port.ini)..."
echo "[INFO] Press CTRL+C to stop the dashboard server."
echo ""

exec $RUNNER main.py --port "$PORT"
