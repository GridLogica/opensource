#!/usr/bin/env python3
import os
import sys

# Ensure all dependencies (fastapi, psutil, httpx, bcrypt, jwt) are installed before importing them
try:
    from bootstrap import ensure_dependencies
    ensure_dependencies()
except Exception as e:
    print(f"[!] Dependency bootstrap warning: {e}")

import time
import json
import signal
import socket
import urllib.request
import subprocess
import argparse
from typing import Optional, Dict, Any, Set

try:
    import psutil
except ImportError:
    psutil = None

from port_config import get_configured_port, get_configured_host, set_configured_port

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, ".service.json")
LOG_FILE = os.path.join(BASE_DIR, "service.log")
ERR_LOG_FILE = os.path.join(BASE_DIR, "service_err.log")


def ensure_venv_ready() -> str:
    """Ensure local .venv exists and has required dependencies installed. Returns python executable path."""
    venv_dir = os.path.join(BASE_DIR, ".venv")
    python_bin = os.path.join(venv_dir, "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(venv_dir, "bin", "python")
    
    if os.path.exists(python_bin):
        try:
            res = subprocess.run([python_bin, "-c", "import fastapi, psutil, httpx, bcrypt, jwt"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return python_bin
        except Exception:
            pass

    print("[*] Virtual environment check: verifying local dependencies in folder...")
    sys_python = sys.executable
    
    if not os.path.exists(python_bin):
        try:
            subprocess.run([sys_python, "-m", "venv", venv_dir], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            python_bin = sys_python

    req_file = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_file):
        try:
            subprocess.run([python_bin, "-m", "pip", "install", "-r", req_file],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    return python_bin if os.path.exists(python_bin) else sys_python


def read_state() -> Optional[Dict[str, Any]]:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_state(pid: Optional[int], port: int, host: str):
    data = {
        "pid": pid,
        "port": port,
        "host": host,
        "base_dir": BASE_DIR,
        "start_time": time.time()
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def clear_state():
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    """Check if any socket is listening on given port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def is_dashboard_server(port: int) -> bool:
    """Verify if a server responding on the port is actually our Homelab Dashboard."""
    try:
        url = f"http://127.0.0.1:{port}/api/v1/config"
        req = urllib.request.Request(url, headers={"User-Agent": "HomelabDashboardCheck"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                body = resp.read().decode("utf-8", errors="ignore")
                return "dashboardTitle" in body or "sections" in body
    except Exception:
        pass
    return False


def find_pid_by_port(port: int) -> Optional[int]:
    """Find PID listening on specific port across Windows and Linux."""
    if sys.platform == "win32":
        try:
            cmd = f'netstat -ano | findstr LISTENING | findstr :{port}'
            out = subprocess.check_output(cmd, shell=True).decode()
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                    return int(parts[-1])
        except Exception:
            pass
    elif psutil:
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    for conn in proc.connections(kind='inet'):
                        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                            return proc.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
    return None


def get_service_pids(port: Optional[int] = None) -> Set[int]:
    """Find process PIDs matching main.py server or listening port."""
    pids = set()
    state = read_state()
    if state and state.get("pid"):
        pids.add(state["pid"])

    target_port = port or (state.get("port") if state else get_configured_port())

    if target_port:
        port_pid = find_pid_by_port(target_port)
        if port_pid:
            pids.add(port_pid)

    if psutil:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                cmd_str = ' '.join(cmdline).lower()
                if 'main.py' in cmd_str:
                    if target_port and str(target_port) in cmd_str:
                        pids.add(proc.info['pid'])
                    elif not target_port:
                        pids.add(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return pids


def get_service_status(requested_port: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve detailed service health & process info."""
    state = read_state()
    port = requested_port or (state.get("port") if state else get_configured_port())
    
    is_dashboard = is_dashboard_server(port)
    pids = get_service_pids(port)
    
    alive_pid = None
    proc_info = None

    if psutil:
        for pid in pids:
            try:
                p = psutil.Process(pid)
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    alive_pid = pid
                    proc_info = {
                        "pid": pid,
                        "name": p.name(),
                        "cpu_percent": p.cpu_percent(interval=0.1),
                        "memory_mb": round(p.memory_info().rss / (1024 * 1024), 1),
                        "create_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time()))
                    }
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    return {
        "running": is_dashboard,
        "pid": alive_pid or (list(pids)[0] if (is_dashboard and pids) else None),
        "port": port,
        "info": proc_info
    }


def start_service(port: Optional[int] = None, host: Optional[str] = None):
    target_port = port or get_configured_port(3000)
    target_host = host or get_configured_host("0.0.0.0")

    # Update port.ini preference
    set_configured_port(target_port, target_host)

    if is_dashboard_server(target_port):
        status = get_service_status(requested_port=target_port)
        print(f"[!] Dashboard is ALREADY RUNNING on port {target_port} (PID: {status['pid'] or 'active'})")
        print(f"[*] Dashboard URL: http://localhost:{target_port}")
        return

    if is_port_listening(target_port):
        print(f"[ERROR] Port {target_port} is already in use by another application (e.g., Cockpit/Nginx/Plex).")
        print(f"[*] Please update port in port.ini or specify a free port (e.g. --port 3000, 8080).")
        return

    python_bin = ensure_venv_ready()
    main_py = os.path.join(BASE_DIR, "main.py")

    print(f"[*] Starting Homelab Dashboard service on {target_host}:{target_port} (configured in port.ini)...")

    env = os.environ.copy()
    env["PORT"] = str(target_port)
    env["HOST"] = target_host

    if sys.platform == "win32":
        cmd_str = f"powershell -Command \"Start-Process -FilePath '{python_bin}' -ArgumentList '{main_py}', '--port', '{target_port}', '--host', '{target_host}' -WorkingDirectory '{BASE_DIR}' -RedirectStandardOutput '{LOG_FILE}' -RedirectStandardError '{ERR_LOG_FILE}' -WindowStyle Hidden\""
        subprocess.run(cmd_str, shell=True, cwd=BASE_DIR, env=env)
    else:
        log_f = open(LOG_FILE, "a", encoding="utf-8")
        err_f = open(ERR_LOG_FILE, "a", encoding="utf-8")
        log_f.write(f"\n--- Service Start: {time.strftime('%Y-%m-%d %H:%M:%S')} (Port {target_port}) ---\n")
        log_f.flush()
        cmd = [python_bin, main_py, "--port", str(target_port), "--host", target_host]
        subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=err_f,
            start_new_session=True
        )

    # Wait up to 3.5 seconds for socket binding and verification
    start_wait = time.time()
    online = False
    while time.time() - start_wait < 3.5:
        if is_dashboard_server(target_port):
            online = True
            break
        time.sleep(0.3)

    actual_pids = get_service_pids(target_port)
    saved_pid = list(actual_pids)[0] if actual_pids else None
    write_state(saved_pid, target_port, target_host)

    if online or is_dashboard_server(target_port):
        print(f"[OK] Service STARTED SUCCESSFULLY on port {target_port}!")
        print(f"[*] Process PID: {saved_pid or 'Running'}")
        print(f"[*] Server Port: {target_port}")
        print(f"[*] Config File: port.ini")
        print(f"[*] Log File:    {LOG_FILE}")
        print(f"[*] Dashboard URL: http://localhost:{target_port}")
    else:
        print(f"[!] Service startup initiated on port {target_port}. Check logs at {LOG_FILE}")


def stop_service(port: Optional[int] = None):
    target_port = port or get_configured_port()
    pids_to_kill = get_service_pids(target_port)

    if not pids_to_kill and not is_dashboard_server(target_port):
        print(f"[INFO] Service is not currently running on port {target_port}.")
        clear_state()
        return

    print(f"[*] Stopping Homelab Dashboard service (Port: {target_port}, PIDs: {list(pids_to_kill)})...")

    for p_id in pids_to_kill:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p_id)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(p_id, signal.SIGTERM)
                time.sleep(0.3)
                try:
                    os.kill(p_id, signal.SIGKILL)
                except OSError:
                    pass
        except Exception as e:
            print(f"[!] Warning stopping PID {p_id}: {e}")

    clear_state()
    time.sleep(0.5)
    print(f"[OK] Service on port {target_port} STOPPED successfully.")


def print_status(target_port: Optional[int] = None):
    port = target_port or get_configured_port()
    status = get_service_status(requested_port=port)
    state = read_state()

    print("==================================================")
    print("        HOMELAB GNOME DASHBOARD SERVICE STATUS    ")
    print("==================================================")

    if status["running"]:
        print(f"Status:       [RUNNING]")
        print(f"Process PID:  {status['pid']}")
        print(f"Server Port:  {status['port']}")
        if status["info"]:
            info = status["info"]
            print(f"Memory Usage: {info['memory_mb']} MB")
            print(f"CPU Usage:    {info['cpu_percent']}%")
            print(f"Started At:   {info['create_time']}")
        print(f"Config File:  port.ini")
        print(f"Log File:     {LOG_FILE}")
        print(f"Dashboard URL: http://localhost:{status['port']}")
    else:
        print("Status:       [STOPPED]")
        print(f"Configured Port (port.ini): {port}")
    print("==================================================")


def interactive_menu():
    while True:
        cfg_port = get_configured_port()
        status = get_service_status(requested_port=cfg_port)
        status_str = f"[RUNNING] (PID: {status['pid']}, Port: {status['port']})" if status['running'] else f"[STOPPED] (Configured Port: {cfg_port})"
        
        print("\n" + "="*50)
        print("     HOMELAB DASHBOARD SERVICE MANAGER")
        print("="*50)
        print(f"Current Status: {status_str}")
        print("-" * 50)
        print(f"1) Start Service (Port {cfg_port} from port.ini)")
        print(f"2) Stop / Kill Service (Port {cfg_port})")
        print("3) Restart Service")
        print("4) Check Service Status")
        print("5) Change Port in port.ini & Start")
        print("0) Exit")
        print("="*50)

        try:
            choice = input("Select an option [0-5]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "1":
            start_service(port=cfg_port)
        elif choice == "2":
            stop_service(port=cfg_port)
        elif choice == "3":
            stop_service(port=cfg_port)
            time.sleep(1)
            start_service(port=cfg_port)
        elif choice == "4":
            print_status(target_port=cfg_port)
        elif choice == "5":
            port_input = input(f"Enter new port (current: {cfg_port}): ").strip()
            if port_input.isdigit():
                new_port = int(port_input)
                set_configured_port(new_port)
                print(f"[OK] Saved port = {new_port} in port.ini")
                start_service(port=new_port)
            else:
                print("[ERROR] Invalid port number.")
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("[ERROR] Invalid choice. Please try again.")


def main():
    parser = argparse.ArgumentParser(description="Homelab GNOME Dashboard Service Controller")
    parser.add_argument("action", nargs="?", choices=["start", "stop", "restart", "status", "menu"], default="menu",
                        help="Action to perform: start, stop, restart, status, menu")
    parser.add_argument("--port", "-p", type=int, default=None, help="Port to listen on (default: read from port.ini)")
    parser.add_argument("--host", type=str, default=None, help="Host IP to bind (default: read from port.ini)")

    args = parser.parse_args()
    port = args.port or get_configured_port()
    host = args.host or get_configured_host()

    if args.action == "start":
        start_service(port=port, host=host)
    elif args.action == "stop":
        stop_service(port=port)
    elif args.action == "restart":
        stop_service(port=port)
        time.sleep(1)
        start_service(port=port, host=host)
    elif args.action == "status":
        print_status(target_port=port)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
