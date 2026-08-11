import os
import configparser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT_INI_FILE = os.path.join(BASE_DIR, "port.ini")


def get_configured_port(default: int = 3000) -> int:
    """Read port from port.ini, fallback to environment variable PORT or default."""
    env_port = os.getenv("PORT")
    if env_port and env_port.isdigit():
        return int(env_port)

    if os.path.exists(PORT_INI_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(PORT_INI_FILE, encoding="utf-8")
            if "server" in config and "port" in config["server"]:
                return config.getint("server", "port")
            elif "DEFAULT" in config and "port" in config["DEFAULT"]:
                return config.getint("DEFAULT", "port")
        except Exception:
            pass
    return default


def get_configured_host(default: str = "0.0.0.0") -> str:
    """Read host IP from port.ini, fallback to environment variable HOST or default."""
    env_host = os.getenv("HOST")
    if env_host:
        return env_host

    if os.path.exists(PORT_INI_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(PORT_INI_FILE, encoding="utf-8")
            if "server" in config and "host" in config["server"]:
                return config.get("server", "host")
        except Exception:
            pass
    return default


def set_configured_port(port: int, host: str = "0.0.0.0"):
    """Write or update port and host in port.ini."""
    try:
        config = configparser.ConfigParser()
        if os.path.exists(PORT_INI_FILE):
            config.read(PORT_INI_FILE, encoding="utf-8")
        if "server" not in config:
            config["server"] = {}
        config["server"]["port"] = str(port)
        config["server"]["host"] = host
        with open(PORT_INI_FILE, "w", encoding="utf-8") as f:
            config.write(f)
    except Exception as e:
        print(f"[!] Warning updating port.ini: {e}")
