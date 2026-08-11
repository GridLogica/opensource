@echo off
setlocal enabledelayedexpansion

:: Always set working directory to folder containing this batch script
cd /d "%~dp0"
title Homelab GNOME Dashboard

set PORT=3000
if not "%~1"=="" (
    set PORT=%~1
) else (
    for /f "usebackq tokens=*" %%A in (`py -3 -c "from port_config import get_configured_port; print(get_configured_port())" 2^>nul`) do (
        set PORT=%%A
    )
)

echo ==================================================
echo   HOMELAB GNOME DASHBOARD - PORTABLE RUNNER
echo ==================================================
echo.

:: Detect Python 3 on system
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set SYS_PYTHON=python
) else (
    py -0 >nul 2>&1
    if %errorlevel% equ 0 (
        set SYS_PYTHON=py -3
    ) else (
        echo [ERROR] Python 3 is not installed or not found in system PATH.
        echo Please install Python 3.10+ from https://www.python.org/
        echo.
        pause
        exit /b 1
    )
)

set VENV_PYTHON=.venv\Scripts\python.exe

:: Ensure virtual environment exists in current directory
if not exist "%VENV_PYTHON%" (
    echo [*] Creating local Python virtual environment (.venv)...
    %SYS_PYTHON% -m venv .venv
    if %errorlevel% neq 0 (
        echo [!] Could not create virtual environment. Falling back to system Python.
        set VENV_PYTHON=%SYS_PYTHON%
    )
)

:: Verify dependencies in virtual environment
"%VENV_PYTHON%" -c "import fastapi, psutil, httpx, bcrypt, jwt" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing required packages from requirements.txt...
    "%VENV_PYTHON%" -m pip install --upgrade pip >nul 2>&1
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Ensure wallpapers directory exists
if not exist "static\wallpapers" mkdir "static\wallpapers"

echo.
echo [OK] Starting Homelab Dashboard on http://localhost:%PORT% (configured in port.ini)...
echo [INFO] Press CTRL+C to stop the dashboard server.
echo.

"%VENV_PYTHON%" main.py --port %PORT%

pause
