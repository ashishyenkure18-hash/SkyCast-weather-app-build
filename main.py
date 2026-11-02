"""SkyCast CLI entry point.

Keeps UI/menu logic separate from weather_service.
"""

import sys

from config import ConfigError, get_api_key
from weather_service import (
    AuthenticationError,
    CityNotFoundError,
    InvalidResponseError,
    NetworkError,
    RateLimitError,
    WeatherError,
    build_short_forecast_text,
    get_current_weather,
    get_forecast,
)

BANNER = "=" * 40


def _safe_print(text: str = "") -> None:
    """Print with fallback for terminals that can't render symbols."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def display_weather(data: dict) -> None:
    """Pretty-print a current weather record."""
    location = data["city"]
    if data.get("country"):
        location = f"{location}, {data['country']}"

    _safe_print()
    _safe_print(BANNER)
    _safe_print("          SKYCAST WEATHER APP")
    _safe_print(BANNER)
    _safe_print()
    _safe_print(f"City: {location}")
    _safe_print(f"Temperature: {data['temperature']:.1f}°C")
    _safe_print(f"Feels Like: {data['feels_like']:.1f}°C")
    if data.get("temp_min") is not None and data.get("temp_max") is not None:
        _safe_print(
            f"Min / Max: {data['temp_min']:.1f}°C / {data['temp_max']:.1f}°C"
        )
    _safe_print(f"Humidity: {data['humidity']}%")
    _safe_print(f"Conditions: {data['description'].capitalize()}")
    if data.get("wind_speed") is not None:
        _safe_print(f"Wind Speed: {data['wind_speed']} m/s")
    if data.get("pressure") is not None:
        _safe_print(f"Pressure: {data['pressure']} hPa")
    _safe_print()
    _safe_print("Data source: OpenWeatherMap")
    _safe_print(BANNER)
    _safe_print()


def prompt_city() -> str | None:
    """Prompt for a city. Returns None if the user cancels."""
    city = input("Enter city name (blank to cancel): ").strip()
    return city or None


def handle_search() -> None:
    city = prompt_city()
    if not city:
        _safe_print("Cancelled.")
        return

    try:
        data = get_current_weather(city)
        display_weather(data)
        _safe_print("Tip: repeated searches within 5 minutes are served from cache.")
    except (CityNotFoundError, AuthenticationError, RateLimitError,
            NetworkError, InvalidResponseError, WeatherError) as exc:
        _safe_print(f"Error: {exc}")


def handle_forecast() -> None:
    city = prompt_city()
    if not city:
        _safe_print("Cancelled.")
        return

    try:
        forecast = get_forecast(city)
        if not forecast:
            _safe_print("No forecast entries available.")
            return
        _safe_print()
        _safe_print(BANNER)
        _safe_print(f"Short Forecast for {city}")
        _safe_print(BANNER)
        _safe_print(build_short_forecast_text(forecast))
        _safe_print()
        for entry in forecast:
            _safe_print(
                f"  {entry['time']}  {entry['temp']:.1f}°C  "
                f"{entry['description']}  ({entry.get('humidity', '?')}% RH)"
            )
        _safe_print(BANNER)
        _safe_print()
    except (CityNotFoundError, AuthenticationError, RateLimitError,
            NetworkError, InvalidResponseError, WeatherError) as exc:
        _safe_print(f"Error: {exc}")


def menu() -> None:
    _safe_print(BANNER)
    _safe_print("          SKYCAST WEATHER APP")
    _safe_print(BANNER)
    while True:
        _safe_print()
        _safe_print("1. Search weather by city")
        _safe_print("2. View a short forecast")
        _safe_print("3. Search another city")
        _safe_print("4. Exit")
        choice = input("Choose an option (1-4): ").strip()

        if choice == "1":
            handle_search()
        elif choice == "2":
            handle_forecast()
        elif choice == "3":
            _safe_print("Enter the next city when prompted below.")
            handle_search()
        elif choice == "4":
            _safe_print("Goodbye from SkyCast!")
            return
        else:
            _safe_print("Please enter 1, 2, 3, or 4.")


def main() -> int:
    try:
        get_api_key()  # fail fast with a friendly message
    except ConfigError as exc:
        _safe_print(f"Configuration error: {exc}")
        _safe_print("See .env.example for the required variable name.")
        return 1
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        _safe_print("\nInterrupted. Exiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())