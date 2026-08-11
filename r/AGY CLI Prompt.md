# **AGY / AI CLI BUILD PROMPT: Homelab GNOME Dashboard (Python Backend)**

## **🎯 OBJECTIVE**

Build a lightweight, production-ready Python web application that serves index.html as a single-page dashboard on a Linux VPS (non-Docker). The application must persist all configuration to the filesystem and replace all frontend mock telemetry with real system endpoints.

## **🛠️ STACK REQUIREMENTS**

* **Language**: Python 3.10+  
* **Framework**: FastAPI \+ Uvicorn (or Flask \+ Gunicorn)  
* **System Monitoring**: psutil  
* **Async HTTP Requests**: httpx  
* **Security**: passlib\[bcrypt\], PyJWT (or simple session tokens)  
* **File Uploads**: python-multipart

## **📁 TARGET PROJECT STRUCTURE**

homelab-dashboard/  
│  
├── main.py                 \# Core API application & routing  
├── config.json             \# Persistent dashboard state (read/write)  
├── requirements.txt        \# Python dependencies  
├── run.sh                  \# Application startup script  
│  
└── static/  
    ├── index.html          \# Frontend HTML/JS/CSS (from repository)  
    └── wallpapers/         \# Target dir for uploaded custom backgrounds

## **⚙️ CRITICAL BACKEND REQUIREMENTS**

### **1\. Persistence via Disk (config.json)**

* **DO NOT** rely on browser localStorage or session memory.  
* On startup, read config.json. If missing, create it using the default state embedded in index.html.  
* Provide endpoints:  
  * GET /api/v1/config \-\> Returns current JSON configuration.  
  * POST /api/v1/config \-\> Overwrites config.json with updated payload from frontend.

### **2\. Custom Wallpaper Uploads (/api/v1/wallpaper)**

* Implement POST /api/v1/wallpaper accepting multipart/form-data.  
* Save uploaded file to static/wallpapers/\<filename\>.  
* Return relative URL path (/static/wallpapers/\<filename\>) to be stored in config.json.

### **3\. Real System Telemetry (/api/v1/stats)**

* Use psutil to measure actual host statistics:  
  * cpu: Host CPU percentage.  
  * ram: Host RAM percentage.  
  * net: Network throughput speed or active bandwidth (e.g., Mbps).  
* Return as JSON or stream over a WebSocket to replace initMockTelemetry().

### **4\. Asynchronous Service Health Check (/api/v1/health)**

* Implement a background worker or endpoint using httpx.AsyncClient with a 3-second timeout.  
* Ping each app URL in config.json.  
* Return dictionary of { app\_id: is\_online\_boolean } so frontend status indicators reflect real service status.

### **5\. Security & Lock PIN (/api/v1/auth/verify-pin)**

* Store security PIN in config.json as a bcrypt hash (never plain text).  
* Implement POST /api/v1/auth/verify-pin to validate PIN input and issue a signed session JWT cookie.

## **🔄 FRONTEND INTEGRATION STEPS FOR index.html**

1. Update loadLocalState() to perform fetch('/api/v1/config') instead of localStorage.getItem().  
2. Update window.saveState() to perform fetch('/api/v1/config', { method: 'POST', body: ... }).  
3. Replace handleWallpaperFileUpload() to fetch('/api/v1/wallpaper', { method: 'POST', body: formData }).  
4. Connect initMockTelemetry() to fetch from /api/v1/stats and /api/v1/health on intervals.

## **🚀 EXECUTION INSTRUCTION FOR CLI AGENT**

Please execute the following actions step-by-step:

1. Create requirements.txt with all dependencies.  
2. Create config.json with the default configuration schema.  
3. Build main.py with FastAPI serving static files and implementing all required API endpoints.  
4. Modify index.html to connect frontend state and telemetry functions to the new FastAPI endpoints.  
5. Provide a systemd unit template (homelab-dash.service) for deployment on Ubuntu/Debian VPS.