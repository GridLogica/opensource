#!/usr/bin/env bash
# Personal Workspace Dashboard v1 - Systemd Service Installer

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="workspace-dashboard-v1"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "============================================================"
echo " Personal Workspace Dashboard v1 - Systemd Service Installer"
echo "============================================================"

if [ "$1" = "--uninstall" ] || [ "$1" = "uninstall" ]; then
    echo "[*] Uninstalling systemd service '${SERVICE_NAME}'..."
    if command -v systemctl &> /dev/null; then
        sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null
        sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null
        if [ -f "${SERVICE_FILE}" ]; then
            sudo rm -f "${SERVICE_FILE}"
            sudo systemctl daemon-reload
        fi
        echo "[✓] Service '${SERVICE_NAME}' uninstalled successfully."
    else
        echo "[X] systemctl is not available on this system."
    fi
    exit 0
fi

# Detect Python 3
PYTHON_BIN=""
if command -v python3 &> /dev/null; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python &> /dev/null; then
    PYTHON_BIN="$(command -v python)"
else
    echo "[X] Error: Python 3 was not found. Please install Python 3."
    exit 1
fi

# Detect Port from config.ini if present
PORT=3000
if [ -f "${APP_DIR}/config.ini" ]; then
    INI_PORT=$(grep -i "^port" "${APP_DIR}/config.ini" | head -n 1 | awk -F'=' '{print $2}' | tr -d ' ')
    if [ -n "$INI_PORT" ]; then
        PORT="$INI_PORT"
    fi
fi

CURRENT_USER="${SUDO_USER:-$USER}"

echo "[*] Application Directory: ${APP_DIR}"
echo "[*] Python Executable:    ${PYTHON_BIN}"
echo "[*] Configured Port:      ${PORT}"
echo "[*] Service User:         ${CURRENT_USER}"

if ! command -v systemctl &> /dev/null; then
    echo "[X] systemctl is not available on this system. Systemd is required for service installation."
    exit 1
fi

echo "[*] Generating systemd unit file at ${SERVICE_FILE}..."

TMP_SERVICE=$(mktemp)
cat <<EOF > "${TMP_SERVICE}"
[Unit]
Description=Personal Workspace Dashboard Server v1
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_BIN} ${APP_DIR}/server.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PORT=${PORT}

[Install]
WantedBy=multi-user.target
EOF

sudo mv "${TMP_SERVICE}" "${SERVICE_FILE}"
sudo chmod 644 "${SERVICE_FILE}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo ""
echo "[✓] Workspace Dashboard installed and started as service '${SERVICE_NAME}.service'!"
echo "[✓] Dashboard active at: http://localhost:${PORT}"
echo "[*] Useful Service Commands:"
echo "    sudo systemctl status ${SERVICE_NAME}"
echo "    sudo systemctl restart ${SERVICE_NAME}"
echo "    sudo systemctl stop ${SERVICE_NAME}"
echo "    ${APP_DIR}/install-service.sh uninstall"
echo "============================================================"
