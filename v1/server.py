#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Personal Workspace Dashboard v1 - Native Python 3 Server
Zero External Dependencies (Uses Python standard library only)
Full Persistent Disk Storage (config.json, config.ini & links.json)
"""

import http.server
import socketserver
import json
import configparser
import os
import time
import platform
import shutil
import subprocess
from urllib.parse import urlparse
from pathlib import Path

PORT = int(os.environ.get("PORT", 3000))
BASE_DIR = Path(__file__).parent.resolve()
CONFIG_JSON_PATH = BASE_DIR / "config.json"
CONFIG_INI_PATH = BASE_DIR / "config.ini"
LINKS_JSON_PATH = BASE_DIR / "links.json"

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".ini": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon"
}

DEFAULT_WALLPAPERS = [
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2070&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=2070&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=2070&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=2070&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=2070&auto=format&fit=crop"
]

DEFAULT_NAVIGATION = [
    {
        "type": "category",
        "title": "Applications & Apps",
        "sublinks": [
            { "title": "All Applications", "action": "modal:modal-services", "badge": "Launch" }
        ]
    },
    {
        "type": "item",
        "title": "System Telemetry",
        "action": "modal:modal-telemetry",
        "badge": "Live"
    },
    {
        "type": "header",
        "title": "Personal Shortcuts"
    },
    {
        "type": "item",
        "title": "GitHub Repositories",
        "url": "https://github.com"
    },
    {
        "type": "category",
        "title": "Options",
        "sublinks": [
            { "title": "Dashboard Settings", "action": "modal:modal-settings" },
            { "title": "Search Commands", "action": "modal:modal-cmd", "shortcut": "⌘K" },
            { "title": "Change Wallpaper", "action": "action:cycleBg" },
            { "title": "Edit JSON Config", "action": "modal:modal-json" }
        ]
    }
]

DEFAULT_SERVICES_GRID = [
    { "name": "Smart Home", "url": "http://homeassistant.local:8123", "subtext": "Automation" },
    { "name": "Jellyfin Media", "url": "http://jellyfin.local:8096", "subtext": "Streaming" },
    { "name": "Nextcloud", "url": "https://nextcloud.local", "subtext": "Personal Cloud" },
    { "name": "Virtual Server", "url": "https://proxmox.local:8006", "subtext": "Infrastructure", "protected": True },
    { "name": "Containers", "url": "https://portainer.local:9443", "subtext": "Docker Manager", "protected": True },
    { "name": "Analytics", "url": "http://grafana.local:3000", "subtext": "Metrics & Dashboards" },
    { "name": "DNS Shield", "url": "http://pihole.local/admin", "subtext": "Ad-Block Guard" },
    { "name": "Storage Pool", "url": "https://truenas.local", "subtext": "NAS Storage", "protected": True }
]

DEFAULT_CONFIG = {
    "nodeName": "My Workspace",
    "nodeBadge": "Workspace",
    "footerStatus": "Workspace Ready",
    "footerTag": "v3.0",
    "clock12h": False,
    "showDate": True,
    "showGreeting": True,
    "clockPosition": "center",
    "fontFamily": "Plus Jakarta Sans",
    "themeMode": "dark",
    "accentTheme": "theme-sky",
    "dimAmount": 25,
    "blurAmount": 0,
    "port": 3000,
    "pinEnabled": True,
    "pinCode": "1234",
    "privacyMode": False,
    "showLockButton": True,
    "showSideDrawer": True,
    "backgrounds": DEFAULT_WALLPAPERS,
    "activeWallpaper": DEFAULT_WALLPAPERS[0],
    "activeWallpaperIndex": 0,
    "navigation": DEFAULT_NAVIGATION,
    "servicesGrid": DEFAULT_SERVICES_GRID,
    "updatedAt": 0
}


def load_ini_config():
    config = configparser.ConfigParser(interpolation=None)
    if CONFIG_INI_PATH.exists():
        try:
            config.read(CONFIG_INI_PATH, encoding="utf-8")
        except Exception as e:
            print(f"Error reading config.ini: {e}")
    return config


def load_links_json():
    if LINKS_JSON_PATH.exists():
        try:
            with open(LINKS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Error reading links.json: {e}")
    return {}


def get_combined_config():
    # 1. Primary: Load from config.json if available
    if CONFIG_JSON_PATH.exists():
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and len(data) > 0:
                    merged = dict(DEFAULT_CONFIG)
                    merged.update(data)
                    return merged
        except Exception as e:
            print(f"Error reading config.json: {e}")

    # 2. Secondary: Fallback to reading config.ini and links.json
    ini = load_ini_config()
    links = load_links_json()

    pin_enabled = ini.getboolean("security", "pinEnabled", fallback=True)
    pin_code = os.environ.get("PIN_CODE") or ini.get("security", "pinCode", fallback="1234")
    port = os.environ.get("PORT")
    port_val = int(port) if (port and port.isdigit()) else ini.getint("server", "port", fallback=3000)

    wallpapers = links.get("backgrounds")
    if not wallpapers or not isinstance(wallpapers, list) or len(wallpapers) == 0:
        wallpapers_raw = ini.get("backgrounds", "wallpapers", fallback="")
        wallpapers = [w.strip() for w in wallpapers_raw.split(",") if w.strip()]
    if not wallpapers:
        wallpapers = DEFAULT_WALLPAPERS

    active_wallpaper = ini.get("backgrounds", "activewallpaper", fallback="") or links.get("activeWallpaper", "")
    try:
        active_wallpaper_index = int(ini.get("backgrounds", "activewallpaperindex", fallback=str(links.get("activeWallpaperIndex", 0))))
    except Exception:
        active_wallpaper_index = 0

    if not active_wallpaper and len(wallpapers) > 0:
        active_wallpaper = wallpapers[active_wallpaper_index % len(wallpapers)]

    nav = links.get("navigation")
    if not isinstance(nav, list):
        nav = DEFAULT_NAVIGATION

    grid = links.get("servicesGrid")
    if not isinstance(grid, list):
        grid = DEFAULT_SERVICES_GRID

    config = {
        "nodeName": ini.get("branding", "nodeName", fallback="My Workspace"),
        "nodeBadge": ini.get("branding", "nodeBadge", fallback="Workspace"),
        "footerStatus": ini.get("branding", "footerStatus", fallback="Workspace Ready"),
        "footerTag": ini.get("branding", "footerTag", fallback="v3.0"),
        "clock12h": ini.getboolean("clock", "clock12h", fallback=False),
        "showDate": ini.getboolean("clock", "showDate", fallback=True),
        "showGreeting": ini.getboolean("clock", "showGreeting", fallback=True),
        "clockPosition": ini.get("clock", "clockPosition", fallback="center"),
        "fontFamily": ini.get("clock", "fontFamily", fallback="Plus Jakarta Sans"),
        "themeMode": ini.get("theme", "themeMode", fallback="dark"),
        "accentTheme": ini.get("theme", "accentTheme", fallback="theme-sky"),
        "dimAmount": ini.getint("theme", "dimAmount", fallback=25),
        "blurAmount": ini.getint("theme", "blurAmount", fallback=0),
        "port": port_val,
        "pinEnabled": pin_enabled,
        "pinCode": str(pin_code),
        "privacyMode": ini.getboolean("security", "privacyMode", fallback=False),
        "showLockButton": ini.getboolean("security", "showLockButton", fallback=True),
        "showSideDrawer": ini.getboolean("branding", "showSideDrawer", fallback=True),
        "backgrounds": wallpapers,
        "activeWallpaper": active_wallpaper,
        "activeWallpaperIndex": active_wallpaper_index,
        "navigation": nav,
        "servicesGrid": grid,
        "updatedAt": int(time.time() * 1000)
    }

    # Save to config.json for future atomic loads
    save_combined_config(config)
    return config


def save_combined_config(full_config):
    if not isinstance(full_config, dict):
        return

    merged = dict(DEFAULT_CONFIG)
    merged.update(full_config)
    merged["updatedAt"] = int(time.time() * 1000)

    # 1. Save PRIMARY config.json
    try:
        with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config.json: {e}")

    # 2. Sync SECONDARY links.json
    links_data = {
        "navigation": merged.get("navigation", DEFAULT_NAVIGATION),
        "servicesGrid": merged.get("servicesGrid", DEFAULT_SERVICES_GRID),
        "backgrounds": merged.get("backgrounds", DEFAULT_WALLPAPERS),
        "activeWallpaper": merged.get("activeWallpaper", DEFAULT_WALLPAPERS[0]),
        "activeWallpaperIndex": merged.get("activeWallpaperIndex", 0)
    }
    try:
        with open(LINKS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(links_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error syncing links.json: {e}")

    # 3. Sync TERTIARY config.ini
    try:
        config = configparser.ConfigParser(interpolation=None)
        config["server"] = { "port": str(merged.get("port", 3000)) }
        config["branding"] = {
            "nodeName": str(merged.get("nodeName", "My Workspace")),
            "nodeBadge": str(merged.get("nodeBadge", "Workspace")),
            "footerStatus": str(merged.get("footerStatus", "Workspace Ready")),
            "footerTag": str(merged.get("footerTag", "v3.0")),
            "showSideDrawer": str(merged.get("showSideDrawer", True)).lower()
        }
        config["clock"] = {
            "clock12h": str(merged.get("clock12h", False)).lower(),
            "showDate": str(merged.get("showDate", True)).lower(),
            "showGreeting": str(merged.get("showGreeting", True)).lower(),
            "clockPosition": str(merged.get("clockPosition", "center")),
            "fontFamily": str(merged.get("fontFamily", "Plus Jakarta Sans"))
        }
        config["theme"] = {
            "themeMode": str(merged.get("themeMode", "dark")),
            "accentTheme": str(merged.get("accentTheme", "theme-sky")),
            "dimAmount": str(merged.get("dimAmount", 25)),
            "blurAmount": str(merged.get("blurAmount", 0))
        }
        config["security"] = {
            "pinEnabled": str(merged.get("pinEnabled", True)).lower(),
            "pinCode": str(merged.get("pinCode", "1234")),
            "privacyMode": str(merged.get("privacyMode", False)).lower(),
            "showLockButton": str(merged.get("showLockButton", True)).lower()
        }
        wallpapers = merged.get("backgrounds", DEFAULT_WALLPAPERS)
        wallpapers_clean = [w for w in wallpapers if isinstance(w, str) and not w.startswith("data:")] if isinstance(wallpapers, list) else []
        config["backgrounds"] = {
            "wallpapers": ", ".join(wallpapers_clean),
            "activewallpaper": str(merged.get("activeWallpaper", "")),
            "activewallpaperindex": str(merged.get("activeWallpaperIndex", 0))
        }
        with open(CONFIG_INI_PATH, "w", encoding="utf-8") as f:
            config.write(f)
    except Exception as e:
        print(f"Error syncing config.ini: {e}")

    return merged


def get_server_port():
    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        return int(env_port)
    config = load_ini_config()
    return config.getint("server", "port", fallback=3000)

PORT = get_server_port()


def get_system_telemetry():
    # 1. Disk Usage
    try:
        total, used, free = shutil.disk_usage(BASE_DIR)
        disk_total_gb = round(total / (1024**3), 1)
        disk_used_gb = round(used / (1024**3), 1)
        disk_free_gb = round(free / (1024**3), 1)
        disk_percent = round((used / total) * 100)
    except Exception:
        disk_total_gb, disk_used_gb, disk_free_gb, disk_percent = 100.0, 50.0, 50.0, 50

    # 2. Memory (RAM) Usage
    ram_percent = 35
    ram_used_gb = "4.0 GB"
    ram_total_gb = "16.0 GB"
    ram_free_gb = "12.0 GB"

    if platform.system() == "Linux":
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem_dict = {}
            for l in lines:
                parts = l.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v_str = parts[1].strip().split()[0]
                    if v_str.isdigit():
                        mem_dict[k] = int(v_str)
            total_kb = mem_dict.get("MemTotal", 0)
            avail_kb = mem_dict.get("MemAvailable", mem_dict.get("MemFree", 0))
            if total_kb > 0:
                used_kb = total_kb - avail_kb
                ram_percent = round((used_kb / total_kb) * 100)
                ram_used_gb = f"{round(used_kb / (1024**2), 1)} GB"
                ram_total_gb = f"{round(total_kb / (1024**2), 1)} GB"
                ram_free_gb = f"{round(avail_kb / (1024**2), 1)} GB"
        except Exception:
            pass
    elif platform.system() == "Windows":
        try:
            cmd = 'wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value'
            res = subprocess.check_output(cmd, shell=True, timeout=2).decode("utf-8", errors="ignore")
            total_kb = 0
            free_kb = 0
            for line in res.splitlines():
                if "TotalVisibleMemorySize" in line:
                    parts = line.split("=")
                    if len(parts) > 1 and parts[1].strip().isdigit():
                        total_kb = int(parts[1].strip())
                elif "FreePhysicalMemory" in line:
                    parts = line.split("=")
                    if len(parts) > 1 and parts[1].strip().isdigit():
                        free_kb = int(parts[1].strip())
            if total_kb > 0:
                used_kb = total_kb - free_kb
                ram_percent = round((used_kb / total_kb) * 100)
                ram_used_gb = f"{round(used_kb / (1024**2), 1)} GB"
                ram_total_gb = f"{round(total_kb / (1024**2), 1)} GB"
                ram_free_gb = f"{round(free_kb / (1024**2), 1)} GB"
        except Exception:
            pass

    # 3. CPU Usage
    cpu_percent = 15
    if platform.system() == "Linux":
        try:
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()[0]
                cpu_count = os.cpu_count() or 1
                cpu_percent = min(100, round((float(load) / cpu_count) * 100))
        except Exception:
            pass
    elif platform.system() == "Windows":
        try:
            cmd = 'wmic cpu get LoadPercentage /Value'
            res = subprocess.check_output(cmd, shell=True, timeout=2).decode("utf-8", errors="ignore")
            for line in res.splitlines():
                if "LoadPercentage" in line:
                    parts = line.split("=")
                    if len(parts) > 1 and parts[1].strip().isdigit():
                        cpu_percent = int(parts[1].strip())
        except Exception:
            pass

    return {
        "cpuPercent": cpu_percent,
        "ramPercent": ram_percent,
        "ramUsed": ram_used_gb,
        "ramTotal": ram_total_gb,
        "ramFree": ram_free_gb,
        "diskPercent": disk_percent,
        "diskUsedGb": disk_used_gb,
        "diskFreeGb": disk_free_gb,
        "diskTotalGb": disk_total_gb,
        "hostname": os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME") or "localhost",
        "platform": f"{platform.system()} {platform.release()}"
    }


class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path_str = parsed.path

        # GET /api/telemetry
        if path_str == "/api/telemetry":
            telemetry_data = get_system_telemetry()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(telemetry_data).encode("utf-8"))
            return

        # GET /api/config
        if path_str == "/api/config":
            combined = get_combined_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(combined, indent=2, ensure_ascii=False).encode("utf-8"))
            return

        # GET /api/links
        if path_str == "/api/links":
            cfg = get_combined_config()
            links_data = {
                "navigation": cfg.get("navigation", DEFAULT_NAVIGATION),
                "servicesGrid": cfg.get("servicesGrid", DEFAULT_SERVICES_GRID),
                "backgrounds": cfg.get("backgrounds", DEFAULT_WALLPAPERS),
                "activeWallpaper": cfg.get("activeWallpaper", DEFAULT_WALLPAPERS[0]),
                "activeWallpaperIndex": cfg.get("activeWallpaperIndex", 0)
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(links_data, indent=2, ensure_ascii=False).encode("utf-8"))
            return

        # Serve Static Files
        rel_path = "index.html" if path_str == "/" else path_str.lstrip("/")
        target_file = (BASE_DIR / rel_path).resolve()

        if not str(target_file).startswith(str(BASE_DIR)):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        if not target_file.exists() or not target_file.is_file():
            target_file = BASE_DIR / "index.html"

        ext = target_file.suffix.lower()
        content_type = MIME_TYPES.get(ext, "application/octet-stream")

        try:
            with open(target_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Server Error: {e}".encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path_str = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"

        # POST /api/config
        if path_str == "/api/config":
            try:
                full_config = json.loads(body_bytes.decode("utf-8"))
                saved = save_combined_config(full_config)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Saved to config.json, config.ini, and links.json", "config": saved}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        # POST /api/links
        if path_str == "/api/links":
            try:
                links_payload = json.loads(body_bytes.decode("utf-8"))
                current = get_combined_config()
                if "navigation" in links_payload:
                    current["navigation"] = links_payload["navigation"]
                if "servicesGrid" in links_payload:
                    current["servicesGrid"] = links_payload["servicesGrid"]
                if "backgrounds" in links_payload:
                    current["backgrounds"] = links_payload["backgrounds"]
                if "activeWallpaper" in links_payload:
                    current["activeWallpaper"] = links_payload["activeWallpaper"]
                if "activeWallpaperIndex" in links_payload:
                    current["activeWallpaperIndex"] = links_payload["activeWallpaperIndex"]

                saved = save_combined_config(current)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Saved to links.json and config.json", "config": saved}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

    def do_PUT(self):
        self.do_POST()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def main():
    config = get_combined_config()
    port = config.get("port", PORT)
    server = ThreadedHTTPServer(("0.0.0.0", port), DashboardRequestHandler)
    print("====================================================")
    print(" Personal Workspace Dashboard Server v1 (Python 3)")
    print(f" URL: http://localhost:{port}")
    print(f" PIN Protection: {'ENABLED' if config.get('pinEnabled') else 'DISABLED (Local Mode)'}")
    print("====================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down cleanly.")
        server.server_close()

if __name__ == "__main__":
    main()
