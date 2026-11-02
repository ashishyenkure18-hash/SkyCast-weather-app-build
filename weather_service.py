"""SkyCast weather service.

Handles OpenWeatherMap API requests, JSON parsing, in-memory caching,
and error handling. UI concerns are kept out of this module.
"""

import time
from typing import Any

import requests

from config import (
    BASE_URL,
    CACHE_TTL,
    REQUEST_TIMEOUT,
    get_api_key,
)


class WeatherError(Exception):
    """Base class for weather service errors."""


class CityNotFoundError(WeatherError):
    """City not found in the API (HTTP 404)."""


class AuthenticationError(WeatherError):
    """Invalid or unactivated API key (HTTP 401)."""


class RateLimitError(WeatherError):
    """API rate limit hit (HTTP 429)."""


class NetworkError(WeatherError):
    """Network failure or timeout."""


class InvalidResponseError(WeatherError):
    """Malformed or incomplete API response."""


# In-memory cache: {city_key: (timestamp, data)}
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(city: str) -> str:
    """Normalize a city name for cache lookup."""
    return city.strip().lower()


def clear_cache() -> None:
    """Clear the cache (useful for tests)."""
    _CACHE.clear()


def _check_cache(city: str) -> dict[str, Any] | None:
    """Return cached data if still fresh, else None."""
    entry = _CACHE.get(_cache_key(city))
    if not entry:
        return None
    timestamp, data = entry
    if time.monotonic() - timestamp < CACHE_TTL:
        return data
    _CACHE.pop(_cache_key(city), None)
    return None


def _store_cache(city: str, data: dict[str, Any]) -> None:
    _CACHE[_cache_key(city)] = (time.monotonic(), data)


def _get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    """Internal GET helper that maps HTTP errors to our exception types."""
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout as exc:
        raise NetworkError(
            "Request timed out. Check your internet connection and try again."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise NetworkError(
            "Could not connect to OpenWeatherMap. Check your internet connection."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise NetworkError(f"Network error: {exc}") from exc

    if response.status_code == 401:
        raise AuthenticationError(
            "Invalid API key (HTTP 401). If you just created your key, it may "
            "take 10 minutes to a few hours to activate. Verify the key at "
            "https://home.openweathermap.org/api_keys"
        )
    if response.status_code == 404:
        raise CityNotFoundError(
            "City not found. Check the spelling or try a nearby larger city."
        )
    if response.status_code == 429:
        raise RateLimitError(
            "Rate limit exceeded (HTTP 429). Please wait a bit before retrying."
        )
    if response.status_code >= 500:
        raise WeatherError(
            f"OpenWeatherMap server error (HTTP {response.status_code}). "
            "Try again later."
        )
    if not response.ok:
        raise WeatherError(
            f"Unexpected API error (HTTP {response.status_code})."
        )

    try:
        return response.json()
    except ValueError as exc:
        raise InvalidResponseError(
            "The API returned a response that is not valid JSON."
        ) from exc


def _parse_current(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields we display from a /weather response."""
    try:
        main = payload["main"]
        weather_list = payload["weather"]
        wind = payload.get("wind", {})
        first = weather_list[0]

        return {
            "city": payload.get("name", "Unknown"),
            "country": payload.get("sys", {}).get("country", ""),
            "temperature": main["temp"],
            "feels_like": main["feels_like"],
            "temp_min": main.get("temp_min"),
            "temp_max": main.get("temp_max"),
            "humidity": main["humidity"],
            "pressure": main.get("pressure"),
            "description": first.get("description", "unknown"),
            "icon": first.get("icon", ""),
            "wind_speed": wind.get("speed"),
        }
    except (KeyError, IndexError, TypeError) as exc:
        raise InvalidResponseError(
            "Unexpected or incomplete weather data in API response."
        ) from exc


def _parse_forecast(payload: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """Extract a short forecast summary from a /forecast response."""
    try:
        items = payload["list"][:limit]
    except (KeyError, TypeError) as exc:
        raise InvalidResponseError(
            "Unexpected or incomplete forecast data in API response."
        ) from exc

    summary = []
    for item in items:
        try:
            summary.append({
                "time": item["dt_txt"],
                "temp": item["main"]["temp"],
                "description": item["weather"][0]["description"],
                "humidity": item["main"].get("humidity"),
            })
        except (KeyError, IndexError, TypeError):
            # Skip any malformed forecast entry rather than crash.
            continue
    return summary


def get_current_weather(city: str) -> dict[str, Any]:
    """Fetch current weather for a city (cached for 5 minutes)."""
    if not city or not city.strip():
        raise WeatherError("City name cannot be empty.")

    cached = _check_cache(city)
    if cached is not None:
        return cached

    params = {
        "q": city.strip(),
        "appid": get_api_key(),
        "units": "metric",
    }
    payload = _get("weather", params)
    parsed = _parse_current(payload)
    _store_cache(city, parsed)
    return parsed


def get_forecast(city: str, limit: int = 8) -> list[dict[str, Any]]:
    """Fetch a short forecast summary for a city.

    Note: This hits the /forecast endpoint separately. We cache it under a
    distinct key so it does not collide with current-weather cache.
    """
    if not city or not city.strip():
        raise WeatherError("City name cannot be empty.")

    cache_key = f"forecast::{_cache_key(city)}"
    entry = _CACHE.get(cache_key)
    if entry and time.monotonic() - entry[0] < CACHE_TTL:
        return entry[1]

    params = {
        "q": city.strip(),
        "appid": get_api_key(),
        "units": "metric",
    }
    payload = _get("forecast", params)
    parsed = _parse_forecast(payload, limit=limit)
    _CACHE[cache_key] = (time.monotonic(), parsed)
    return parsed


def build_short_forecast_text(forecast: list[dict[str, Any]]) -> str:
    """Turn forecast entries into a short human-readable summary."""
    if not forecast:
        return "No forecast data available."

    descriptions = {f["description"] for f in forecast}
    temps = [f["temp"] for f in forecast if isinstance(f.get("temp"), (int, float))]

    if temps:
        lo, hi = min(temps), max(temps)
        temp_phrase = f"Temperatures expected between {lo:.0f}°C and {hi:.0f}°C."
    else:
        temp_phrase = "Temperature range unavailable."

    desc_phrase = "Conditions: " + ", ".join(sorted(descriptions)) + "."

    return f"{desc_phrase} {temp_phrase}"