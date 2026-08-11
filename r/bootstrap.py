import os
import sys
import subprocess


def ensure_dependencies():
    """Checks for required dependencies and auto-installs them via pip or apt if missing."""
    required_checks = [
        ("fastapi", "fastapi>=0.100.0"),
        ("uvicorn", "uvicorn[standard]>=0.20.0"),
        ("psutil", "psutil>=5.9.0"),
        ("httpx", "httpx>=0.24.0"),
        ("passlib", "passlib[bcrypt]>=1.7.4"),
        ("bcrypt", "bcrypt>=4.0.0"),
        ("jwt", "PyJWT>=2.8.0"),
        ("multipart", "python-multipart>=0.0.6")
    ]

    missing = []
    for mod_name, pkg_name in required_checks:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if not missing:
        return

    print(f"[!] Missing required Python packages: {', '.join(missing)}")
    print("[*] Attempting automatic package installation...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(base_dir, "requirements.txt")

    pip_base = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    installed = False

    # 1. Try pip install with current python environment
    try:
        targets = ["-r", req_file] if os.path.exists(req_file) else missing
        if sys.platform != "win32":
            # Support modern Debian/Ubuntu PEP 668 externally managed environment flag
            res = subprocess.run(pip_base + ["--break-system-packages"] + targets,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                installed = True
            else:
                res2 = subprocess.run(pip_base + targets,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res2.returncode == 0:
                    installed = True
        else:
            res = subprocess.run(pip_base + targets)
            if res.returncode == 0:
                installed = True
    except Exception as e:
        print(f"[!] Pip installation attempt failed: {e}")

    # 2. On Linux, if pip failed or missing, try apt-get system packages if root/sudo
    if not installed and sys.platform != "win32":
        print("[*] Attempting system package installation via apt-get...")
        apt_packages = [
            "python3-pip", "python3-fastapi", "python3-uvicorn", 
            "python3-psutil", "python3-httpx", "python3-passlib", 
            "python3-bcrypt", "python3-jwt", "python3-multipart"
        ]
        try:
            if hasattr(os, 'geteuid') and os.geteuid() == 0:
                subprocess.run(["apt-get", "update", "-qq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["apt-get", "install", "-y"] + apt_packages, check=True)
                installed = True
            else:
                print(f"[!] Note: To install system packages via apt, run:\n    sudo apt-get update && sudo apt-get install -y {' '.join(apt_packages)}")
        except Exception as e:
            print(f"[!] Apt installation failed: {e}")

    # Final verification check
    still_missing = []
    for mod_name, pkg_name in required_checks:
        try:
            __import__(mod_name)
        except ImportError:
            still_missing.append(pkg_name)

    if still_missing:
        print("[ERROR] Could not automatically install: " + ", ".join(still_missing))
        print("Please run manually:\n  pip install -r requirements.txt\nor\n  sudo apt-get update && sudo apt-get install -y python3-pip python3-fastapi python3-psutil python3-httpx")
    else:
        print("[OK] All required dependencies successfully installed!")


if __name__ == "__main__":
    ensure_dependencies()
