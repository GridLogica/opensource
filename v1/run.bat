@echo off
TITLE Personal Workspace Dashboard v1
COLOR 0A
CD /D "%~dp0"

echo ============================================================
echo   Personal Workspace Dashboard v1 (Python 3)
echo ============================================================
echo.

py -3 --version >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Starting server with Python 3...
    echo.
    py -3 server.py
    goto END
)

python3 --version >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Starting server with python3...
    echo.
    python3 server.py
    goto END
)

python --version >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Starting server with python...
    echo.
    python server.py
    goto END
)

COLOR 0C
echo [ERROR] Python 3 was not found on your system!
echo Please install Python 3 from https://www.python.org/ or Microsoft Store.
echo.

:END
if %errorlevel% neq 0 (
    COLOR 0C
    echo [!] Server process exited with code %errorlevel%.
)

echo.
echo Press any key to exit...
pause >nul
