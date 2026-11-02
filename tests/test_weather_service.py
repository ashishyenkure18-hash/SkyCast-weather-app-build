"""Automated tests for SkyCast's weather_service using mocked API responses."""

import unittest
from unittest import mock

import requests

import weather_service as ws
from config import ConfigError


SAMPLE_CURRENT = {
    "name": "Pune",
    "sys": {"country": "IN"},
    "main": {
        "temp": 29.3,
        "feels_like": 32.1,
        "temp_min": 28.0,
        "temp_max": 30.0,
        "humidity": 65,
        "pressure": 1008,
    },
    "weather": [{"description": "partly cloudy", "icon": "02d"}],
    "wind": {"speed": 3.5},
}

SAMPLE_FORECAST = {
    "list": [
        {
            "dt_txt": "2026-11-02 09:00:00",
            "main": {"temp": 28.0, "humidity": 60},
            "weather": [{"description": "light rain"}],
        },
        {
            "dt_txt": "2026-11-02 12:00:00",
            "main": {"temp": 31.0, "humidity": 55},
            "weather": [{"description": "clear sky"}],
        },
    ]
}


def _mock_response(status=200, json_data=None, raise_json=False):
    resp = mock.Mock(spec=requests.Response)
    resp.status_code = status
    resp.ok = 200 <= status < 300
    if raise_json:
        resp.json.side_effect = ValueError("bad json")
    else:
        resp.json.return_value = json_data or {}
    return resp


class WeatherServiceTests(unittest.TestCase):
    def setUp(self):
        ws.clear_cache()

    # 1. Valid city
    @mock.patch("weather_service.requests.get")
    def test_valid_city(self, mock_get):
        mock_get.return_value = _mock_response(200, SAMPLE_CURRENT)
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            data = ws.get_current_weather("Pune")
        self.assertEqual(data["city"], "Pune")
        self.assertAlmostEqual(data["temperature"], 29.3)
        self.assertEqual(data["humidity"], 65)

    # 2. Unknown city
    @mock.patch("weather_service.requests.get")
    def test_unknown_city(self, mock_get):
        mock_get.return_value = _mock_response(404, {"cod": "404"})
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            with self.assertRaises(ws.CityNotFoundError):
                ws.get_current_weather("Nowhereville")

    # 3. Missing API key
    def test_missing_api_key(self):
        # Simulate config.get_api_key raising ConfigError because env is missing.
        with mock.patch("weather_service.get_api_key",
                        side_effect=ConfigError("missing")):
            with self.assertRaises(ConfigError):
                ws.get_current_weather("Pune")

    # 4. Invalid API key -> 401
    @mock.patch("weather_service.requests.get")
    def test_invalid_api_key(self, mock_get):
        mock_get.return_value = _mock_response(401, {"cod": 401})
        with mock.patch("weather_service.get_api_key", return_value="bad"):
            with self.assertRaises(ws.AuthenticationError):
                ws.get_current_weather("Pune")

    # 5. Network timeout
    @mock.patch("weather_service.requests.get",
                side_effect=requests.exceptions.Timeout())
    def test_timeout(self, _mock_get):
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            with self.assertRaises(ws.NetworkError):
                ws.get_current_weather("Pune")

    # 6. Caching: same city twice -> one HTTP call
    @mock.patch("weather_service.requests.get")
    def test_cache_hit(self, mock_get):
        mock_get.return_value = _mock_response(200, SAMPLE_CURRENT)
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            ws.get_current_weather("Pune")
            ws.get_current_weather("  pune  ")  # normalized
        self.assertEqual(mock_get.call_count, 1)

    # 7. Incomplete JSON
    @mock.patch("weather_service.requests.get")
    def test_incomplete_json(self, mock_get):
        mock_get.return_value = _mock_response(200, {"name": "Pune"})
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            with self.assertRaises(ws.InvalidResponseError):
                ws.get_current_weather("Pune")

    # Bonus: forecast parsing
    @mock.patch("weather_service.requests.get")
    def test_forecast_parsing(self, mock_get):
        mock_get.return_value = _mock_response(200, SAMPLE_FORECAST)
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            forecast = ws.get_forecast("Pune")
        self.assertEqual(len(forecast), 2)
        self.assertEqual(forecast[0]["description"], "light rain")

    # Bonus: invalid JSON
    @mock.patch("weather_service.requests.get")
    def test_invalid_json(self, mock_get):
        mock_get.return_value = _mock_response(200, raise_json=True)
        with mock.patch("weather_service.get_api_key", return_value="testkey"):
            with self.assertRaises(ws.InvalidResponseError):
                ws.get_current_weather("Pune")


if __name__ == "__main__":
    unittest.main()