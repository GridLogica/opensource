#!/usr/bin/env bash
# Personal Workspace Dashboard - Process & Service Terminator

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="workspace-dashboard-v1"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "============================================================"
echo " Personal Workspace Dashboard v1 - Process & Service Killer"
echo "============================================================"

# Read Port from config.ini
PORT=3000
if [ -n "$PORT_ENV" ]; then
    PORT="$PORT_ENV"
elif [ -f "${APP_DIR}/config.ini" ]; then
    INI_PORT=$(grep -i "^port" "${APP_DIR}/config.ini" | head -n 1 | awk -F'=' '{print $2}' | tr -d ' \r')
    if [ -n "$INI_PORT" ]; then
        PORT="$INI_PORT"
    fi
fi

echo "[*] Target Configured Port: ${PORT}"

# Parse command line flags
AUTO_REMOVE_SERVICE=false
SKIP_SERVICE_PROMPT=false

for arg in "$@"; do
    case $arg in
        -y|--yes|--remove-service)
            AUTO_REMOVE_SERVICE=true
            ;;
        --keep-service)
            SKIP_SERVICE_PROMPT=true
            ;;
    esac
done

# Step 1: Kill process running on the configured port
echo "[*] Checking for active processes listening on port ${PORT}..."

PIDS=""
if command -v lsof &> /dev/null; then
    PIDS=$(lsof -ti:${PORT} 2>/dev/null)
elif command -v fuser &> /dev/null; then
    PIDS=$(fuser ${PORT}/tcp 2>/dev/null)
elif command -v ss &> /dev/null; then
    PIDS=$(ss -tulpn "sport = :${PORT}" 2>/dev/null | grep -oP 'pid=\K\d+')
fi

if [ -n "$PIDS" ]; then
    echo "[!] Found active process PID(s) on port ${PORT}: ${PIDS}"
    for pid in $PIDS; do
        echo "[*] Terminating process ${pid}..."
        kill -9 "${pid}" 2>/dev/null || sudo kill -9 "${pid}" 2>/dev/null
    done
else
    echo "[✓] No processes currently listening on port ${PORT}."
fi

# Step 2: Also kill any remaining Python server.py process
SERVER_PIDS=$(pgrep -f "server.py" 2>/dev/null)
if [ -n "$SERVER_PIDS" ]; then
    echo "[!] Found server.py process PID(s): ${SERVER_PIDS}"
    for pid in $SERVER_PIDS; do
        echo "[*] Terminating server.py process ${pid}..."
        kill -9 "${pid}" 2>/dev/null || sudo kill -9 "${pid}" 2>/dev/null
    done
fi

echo "[✓] Port ${PORT} and server processes are clean."

# Step 3: Check for systemd service and offer removal
if command -v systemctl &> /dev/null; then
    SERVICE_EXISTS=false
    if systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null | grep -q "${SERVICE_NAME}"; then
        SERVICE_EXISTS=true
    elif [ -f "${SERVICE_FILE}" ]; then
        SERVICE_EXISTS=true
    fi

    if [ "$SERVICE_EXISTS" = true ] && [ "$SKIP_SERVICE_PROMPT" = false ]; then
        echo ""
        echo "[!] Detected installed systemd service '${SERVICE_NAME}'."

        REMOVE=""
        if [ "$AUTO_REMOVE_SERVICE" = true ]; then
            REMOVE="y"
        else
            read -p "[?] Would you like to stop & remove the systemd service '${SERVICE_NAME}'? (y/N): " REMOVE
        fi

        if [[ "$REMOVE" =~ ^[Yy]$ ]]; then
            echo "[*] Stopping and disabling systemd service '${SERVICE_NAME}'..."
            sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null
            sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null
            if [ -f "${SERVICE_FILE}" ]; then
                sudo rm -f "${SERVICE_FILE}"
                sudo systemctl daemon-reload
            fi
            echo "[✓] Service '${SERVICE_NAME}' stopped and removed."
        else
            echo "[*] Keeping systemd service structure intact."
        fi
    fi
fi

echo "============================================================"
