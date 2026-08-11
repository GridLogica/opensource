import os
import sys

# Ensure all dependencies (fastapi, psutil, httpx, bcrypt, jwt) are installed before importing them
try:
    from bootstrap import ensure_dependencies
    ensure_dependencies()
except Exception as e:
    print(f"[!] Dependency bootstrap warning: {e}")

import json
import time
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, File, UploadFile, HTTPException, Response, Request, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil
import httpx
import bcrypt
import jwt

from port_config import get_configured_port, get_configured_host

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
WALLPAPERS_DIR = os.path.join(STATIC_DIR, "wallpapers")

# Ensure required directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(WALLPAPERS_DIR, exist_ok=True)

# JWT Security Config
JWT_SECRET = os.getenv("JWT_SECRET", "homelab-gnome-dashboard-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Default Configuration State
DEFAULT_CONFIG: Dict[str, Any] = {
    "dashboardTitle": "Homelab Dashboard",
    "dashboardSubtitle": "All systems operational",
    "showBranding": True,
    "useGnomePanel": False,
    "favPanelEnabled": True,
    "favTriggerMode": "hover",
    "favPanelPosition": "left",
    "sections": [
        {"id": "sec-infra", "name": "Infrastructure & Servers", "icon": "fa-server", "isFavorite": True},
        {"id": "sec-smarthome", "name": "Smart Home & Automation", "icon": "fa-house-signal", "isFavorite": False},
        {"id": "sec-media", "name": "Media & Entertainment", "icon": "fa-film", "isFavorite": False}
    ],
    "apps": [
        {"id": "1", "sectionId": "sec-infra", "name": "Proxmox VE", "url": "https://192.168.1.100:8006", "icon": "fa-server", "desc": "Hypervisor Node", "color": "from-orange-600 to-red-600", "isFavorite": True},
        {"id": "2", "sectionId": "sec-smarthome", "name": "Home Assistant", "url": "http://192.168.1.10:8123", "icon": "fa-house-signal", "desc": "Smart Home Hub", "color": "from-blue-500 to-indigo-600", "isFavorite": True},
        {"id": "3", "sectionId": "sec-infra", "name": "Portainer", "url": "http://192.168.1.10:9000", "icon": "fa-docker", "desc": "Container Manager", "color": "from-blue-600 to-blue-800", "isFavorite": False},
        {"id": "4", "sectionId": "sec-infra", "name": "Pi-hole", "url": "http://192.168.1.5/admin", "icon": "fa-shield-halved", "desc": "DNS Network Shield", "color": "from-emerald-500 to-teal-700", "isFavorite": False},
        {"id": "5", "sectionId": "sec-media", "name": "Plex Media", "url": "http://192.168.1.10:32400", "icon": "fa-film", "desc": "Media Server", "color": "from-amber-500 to-orange-600", "isFavorite": False},
        {"id": "6", "sectionId": "sec-media", "name": "Grafana", "url": "http://192.168.1.10:3000", "icon": "fa-chart-area", "desc": "Metrics & Charts", "color": "from-slate-600 to-slate-800", "isFavorite": False}
    ],
    "pinEnabled": False,
    "pinCode": "",
    "pinHash": "",
    "wallpaper": "default",
    "customWallpaperUrl": "",
    "showIcons": True,
    "showStats": True,
    "fontFamily": "inter",
    "clockPosition": "bottom-right"
}

# Network Bandwidth Tracking State
_last_net_bytes = 0
_last_net_time = time.time()
try:
    _io = psutil.net_io_counters()
    if _io:
        _last_net_bytes = _io.bytes_sent + _io.bytes_recv
except Exception:
    pass


def hash_pin_string(pin: str) -> str:
    """Hash a PIN using bcrypt."""
    pin_bytes = pin.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin_bytes, salt).decode("utf-8")


def verify_pin_code(submitted_pin: str, config_data: Dict[str, Any]) -> bool:
    """Validate submitted PIN against bcrypt hash or fallback PIN."""
    pin_hash = config_data.get("pinHash", "")
    if pin_hash:
        try:
            return bcrypt.checkpw(submitted_pin.encode("utf-8")[:72], pin_hash.encode("utf-8"))
        except Exception:
            return False
    
    # Fallback if pinEnabled is true but pinHash not set yet
    fallback_pin = config_data.get("pinCode", "1234") or "1234"
    return submitted_pin == fallback_pin


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"[Error] Failed to read config.json: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    # Check if a plain pinCode was submitted to be hashed
    pin_code = config_data.get("pinCode")
    if pin_code and isinstance(pin_code, str) and pin_code.strip():
        config_data["pinHash"] = hash_pin_string(pin_code.strip())
        config_data["pinCode"] = ""  # Strip plain PIN before saving to disk
    
    # Write updated config to disk
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
    return config_data


def sanitize_config_for_client(config_data: Dict[str, Any]) -> Dict[str, Any]:
    client_config = config_data.copy()
    # Never leak plain PIN or hash to client
    client_config["pinCode"] = ""
    client_config.pop("pinHash", None)
    return client_config


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Initialize FastAPI App
app = FastAPI(title="Homelab GNOME Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas
class PinVerifyRequest(BaseModel):
    pin: str


# Initialize config on startup
@app.on_event("startup")
async def startup_event():
    load_config()
    psutil.cpu_percent(interval=None)


# API Routes
@app.get("/api/v1/config")
async def get_config():
    """Retrieve persistent dashboard configuration."""
    cfg = load_config()
    return sanitize_config_for_client(cfg)


@app.post("/api/v1/config")
async def update_config(payload: Dict[str, Any]):
    """Overwrite config.json with updated state from frontend."""
    current_cfg = load_config()
    
    # Preserve existing pinHash if payload does not supply new pinCode
    if "pinHash" not in payload and "pinHash" in current_cfg:
        payload["pinHash"] = current_cfg["pinHash"]
        
    saved_cfg = save_config(payload)
    return {
        "status": "success",
        "message": "Configuration updated successfully",
        "config": sanitize_config_for_client(saved_cfg)
    }


@app.post("/api/v1/wallpaper")
async def upload_wallpaper(file: UploadFile = File(...)):
    """Save uploaded wallpaper image to static/wallpapers/ and return relative path."""
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"}
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in allowed_extensions:
        ext = ".png"

    filename = f"wallpaper_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
    file_path = os.path.join(WALLPAPERS_DIR, filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    relative_url = f"/static/wallpapers/{filename}"
    return {"url": relative_url, "filename": filename, "status": "success"}


@app.get("/api/v1/stats")
async def get_stats():
    """Get real-time host CPU, RAM, and network throughput using psutil."""
    global _last_net_bytes, _last_net_time
    
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    
    current_time = time.time()
    time_diff = max(current_time - _last_net_time, 0.1)
    
    mbps = 0.0
    try:
        net_io = psutil.net_io_counters()
        if net_io:
            current_bytes = net_io.bytes_sent + net_io.bytes_recv
            byte_diff = current_bytes - _last_net_bytes
            if byte_diff < 0:
                byte_diff = 0
            mbps = round((byte_diff * 8) / (time_diff * 1_000_000), 1)
            _last_net_bytes = current_bytes
            _last_net_time = current_time
    except Exception:
        mbps = 0.0

    return {
        "cpu": round(cpu, 1),
        "ram": round(ram, 1),
        "net": f"{mbps} Mbps",
        "net_mbps": mbps
    }


@app.websocket("/api/v1/stats/ws")
async def websocket_stats(websocket: WebSocket):
    """Stream real-time host system statistics over WebSocket."""
    await websocket.accept()
    try:
        while True:
            stats = await get_stats()
            await websocket.send_json(stats)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.get("/api/v1/health")
async def check_services_health():
    """Asynchronous service health checks for configured applications."""
    cfg = load_config()
    apps = cfg.get("apps", [])
    health_results: Dict[str, bool] = {}

    async def ping_url(app_id: str, url: str):
        if not url or not url.startswith(("http://", "https://")):
            health_results[app_id] = False
            return
        
        try:
            async with httpx.AsyncClient(timeout=3.0, verify=False, follow_redirects=True) as client:
                res = await client.get(url)
                health_results[app_id] = (200 <= res.status_code < 400)
        except Exception:
            health_results[app_id] = False

    tasks = [ping_url(app["id"], app.get("url", "")) for app in apps if "id" in app]
    if tasks:
        await asyncio.gather(*tasks)

    return health_results


@app.post("/api/v1/auth/verify-pin")
async def verify_pin(payload: PinVerifyRequest, response: Response):
    """Verify security PIN and issue JWT session cookie."""
    cfg = load_config()
    is_valid = verify_pin_code(payload.pin, cfg)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN code"
        )
    
    token = create_access_token(data={"sub": "homelab_user"})
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=JWT_EXPIRATION_HOURS * 3600,
        samesite="lax"
    )
    
    return {
        "success": True,
        "token": token,
        "message": "PIN authenticated successfully"
    }


# Serve Static Files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serve the single-page application dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="static/index.html not found")
    return FileResponse(index_path)


if __name__ == "__main__":
    import argparse
    import uvicorn

    default_port = get_configured_port(3000)
    default_host = get_configured_host("0.0.0.0")

    parser = argparse.ArgumentParser(description="Homelab Dashboard Server")
    parser.add_argument("--port", "-p", type=int, default=default_port, help=f"Port to listen on (default: {default_port})")
    parser.add_argument("--host", type=str, default=default_host, help=f"Host IP to bind (default: {default_host})")
    args = parser.parse_args()

    uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
