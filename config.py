"""Configuration loader for SkyCast.

Loads the OpenWeatherMap API key from environment variables (via .env)
and validates it before use.
"""

import os

from dotenv import load_dotenv

# Load .env once at import time. override=False means real OS env vars win.
load_dotenv(override=False)

OPENWEATHER_API_KEY: str | None = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5"
REQUEST_TIMEOUT = 8  # seconds
CACHE_TTL = 300  # 5 minutes


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def get_api_key() -> str:
    """Return the API key or raise ConfigError if missing/placeholder."""
    key = OPENWEATHER_API_KEY

    if not key:
        raise ConfigError(
            "OPENWEATHER_API_KEY is not set. "
            "Create a .env file with OPENWEATHER_API_KEY=your_key_here "
            "or set the environment variable."
        )

    if key.strip().lower() in {"your_api_key_here", "your_actual_api_key_here"}:
        raise ConfigError(
            "OPENWEATHER_API_KEY still contains the placeholder value. "
            "Replace it with your real key from https://home.openweathermap.org/api_keys"
        )

    return key.strip()


def mask_key(key: str) -> str:
    """Return a masked version of the key for logging (never show real key)."""
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"