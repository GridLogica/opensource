#!/usr/bin/env bash
# Workspace Dashboard Launcher v1 (Linux / macOS)

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

if [ "$1" = "--install-service" ] || [ "$1" = "service" ] || [ "$1" = "install" ]; then
    bash "$APP_DIR/install-service.sh" "$@"
    exit $?
fi

if [ "$1" = "--uninstall-service" ] || [ "$1" = "uninstall" ]; then
    bash "$APP_DIR/install-service.sh" uninstall
    exit $?
fi

if [ "$1" = "--kill" ] || [ "$1" = "kill" ] || [ "$1" = "stop" ]; then
    bash "$APP_DIR/kill.sh" "${@:2}"
    exit $?
fi

if [ "$1" = "--status" ] || [ "$1" = "status" ]; then
    if command -v systemctl &> /dev/null; then
        systemctl status workspace-dashboard-v1.service
    else
        echo "[!] systemctl not available."
    fi
    exit 0
fi

if command -v python3 &> /dev/null; then
    python3 server.py
elif command -v python &> /dev/null; then
    python server.py
else
    echo "[X] Python 3 was not found. Please install Python 3."
    exit 1
fi
