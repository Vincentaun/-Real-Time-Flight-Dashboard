import os
from typing import Optional


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def _parse_env_line(line: str) -> Optional[tuple]:
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    if '=' not in line:
        return None
    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return key, value


def load_env(path: str = ENV_PATH) -> None:
    """Simple .env loader: sets environment variables from KEY=VALUE lines."""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for raw in f:
                    parsed = _parse_env_line(raw)
                    if parsed:
                        key, value = parsed
                        os.environ.setdefault(key, value)
    except Exception:
        # Do not crash on env load errors; validation will catch missing keys
        pass


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    val = os.environ.get(key, default)
    if required and (val is None or str(val).strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


# Load .env at import time
load_env()

# TDX configuration
TDX_APP_ID = get_env("TDX_APP_ID", required=True)
TDX_APP_KEY = get_env("TDX_APP_KEY", required=True)
AUTH_URL = get_env(
    "TDX_AUTH_URL",
    default="https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
)
API_URL = get_env(
    "TDX_API_URL",
    default="https://tdx.transportdata.tw/api/basic/v2/Air/FIDS/Airport/Arrival?%24top=200&%24format=JSON",
)

# Some modules use DATA_URL naming; keep a compatible alias
DATA_URL = API_URL

# General app settings
REFRESH_INTERVAL = int(get_env("REFRESH_INTERVAL", default="60"))
CACHE_FILE = get_env("CACHE_FILE", default="flight_data_cache.csv")

# Email notifications
ENABLE_EMAIL_NOTIFICATIONS = get_env("ENABLE_EMAIL_NOTIFICATIONS", default="false").lower() == "true"

SMTP_HOST = get_env("SMTP_HOST", default="smtp.gmail.com")
SMTP_PORT = int(get_env("SMTP_PORT", default="587"))
SMTP_USERNAME = get_env("SMTP_USERNAME", default=None, required=ENABLE_EMAIL_NOTIFICATIONS)
SMTP_PASSWORD = get_env("SMTP_PASSWORD", default=None, required=ENABLE_EMAIL_NOTIFICATIONS)
SMTP_FROM = get_env("SMTP_FROM", default=None, required=ENABLE_EMAIL_NOTIFICATIONS)
SMTP_TO = get_env("SMTP_TO", default=None, required=ENABLE_EMAIL_NOTIFICATIONS)