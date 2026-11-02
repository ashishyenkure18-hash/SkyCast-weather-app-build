# SkyCast – Python Weather Forecast Application

SkyCast is a beginner-friendly CLI app that fetches **live weather** from
[OpenWeatherMap](https://openweathermap.org/) and shows current conditions plus a
short forecast — with clean error handling, API key security, and 5-minute caching.

## Objectives
- Demonstrate real REST API integration from Python.
- Parse JSON safely and validate responses.
- Practice secure secret management with `.env`.
- Show how caching reduces redundant API traffic.

## Features
- Search any supported city by name (Celsius, metric units)
- Current temp, feels-like, min/max, humidity, description, wind, pressure
- Short forecast from OpenWeatherMap's 5-day/3-hour endpoint
- 5-minute in-memory cache (case-insensitive city key)
- Friendly messages for 401 / 404 / 429 / timeouts / bad JSON
- Automated `unittest` suite with mocked HTTP (no live calls)

## Technologies
Python 3.10+, `requests`, `python-dotenv`, `unittest`.

## Prerequisites
- Python 3.10+ ([python.org](https://www.python.org/downloads/))
- An OpenWeatherMap account (free tier is fine)
- Windows PowerShell, macOS Terminal, or Linux shell

## 1. Get an API Key
1. Sign up at <https://home.openweathermap.org/users/sign_up>.
2. Open <https://home.openweathermap.org/api_keys> and copy the default key.
3. **New keys can take 10 minutes to a few hours to activate.** A 401 on a fresh
   key usually means it hasn't activated yet.

## 2. Create a Virtual Environment
### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
# If blocked: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned