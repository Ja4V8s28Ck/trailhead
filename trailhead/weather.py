"""Weather fetching from Open-Meteo (free, no API key)."""

from __future__ import annotations

from datetime import datetime

import httpx
import streamlit as st

from trailhead.models import Location, WeatherData

# WMO Weather codes mapping
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def wmo_description(code: int) -> str:
    """Get human-readable description for WMO weather code."""
    return WMO_CODES.get(code, f"Unknown (code {code})")


def wind_direction(degrees: float) -> str:
    """Convert wind degrees to cardinal direction."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return dirs[idx]


@st.cache_data(ttl=300)  # 5-minute cache
def geocode_city(city_name: str) -> Location | None:
    """
    Geocode a city name using Open-Meteo's free geocoding API.
    Returns Location or None if not found.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "en",
        "format": "json",
    }
    try:
        resp = httpx.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None
        r = results[0]
        return Location(
            name=r.get("name", city_name),
            latitude=r["latitude"],
            longitude=r["longitude"],
            timezone=r.get("timezone", "UTC"),
        )
    except (httpx.HTTPError, KeyError, ValueError):
        return None


@st.cache_data(ttl=300)  # 5-minute cache
def fetch_weather(latitude: float, longitude: float, timezone: str) -> WeatherData | None:
    """
    Fetch current weather from Open-Meteo.
    Returns WeatherData or None on failure.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "weather_code",
            "precipitation",
            "is_day",
        ],
        "daily": ["sunrise", "sunset"],
        "timezone": timezone,
        "forecast_days": 1,
    }
    try:
        resp = httpx.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        current = data["current"]
        daily = data["daily"]

        # Parse sunrise/sunset
        sunrise_str = daily["sunrise"][0]
        sunset_str = daily["sunset"][0]
        sunrise = datetime.fromisoformat(sunrise_str)
        sunset = datetime.fromisoformat(sunset_str)

        # Ensure timezone-aware
        if sunrise.tzinfo is None:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone)
            sunrise = sunrise.replace(tzinfo=tz)
            sunset = sunset.replace(tzinfo=tz)

        now = datetime.now(sunrise.tzinfo)
        daylight_remaining = int((sunset - now).total_seconds() / 60)
        is_daylight = bool(current["is_day"])

        temp_c = current["temperature_2m"]
        temp_f = temp_c * 9 / 5 + 32

        return WeatherData(
            temperature_c=temp_c,
            temperature_f=temp_f,
            wind_speed_kmh=current["wind_speed_10m"],
            wind_direction=wind_direction(current["wind_direction_10m"]),
            weather_code=current["weather_code"],
            weather_description=wmo_description(current["weather_code"]),
            precipitation_mm=current["precipitation"],
            relative_humidity=current["relative_humidity_2m"],
            sunrise=sunrise.isoformat(),
            sunset=sunset.isoformat(),
            daylight_remaining_minutes=max(0, daylight_remaining),
            is_daylight=is_daylight,
        )
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return None


def format_weather_summary(weather: WeatherData) -> str:
    """Create a brief weather summary for display."""
    temp_str = f"{weather.temperature_c:.0f}°C / {weather.temperature_f:.0f}°F"
    precip = (
        f", {weather.precipitation_mm:.1f}mm rain"
        if weather.precipitation_mm > 0
        else ""
    )
    daylight = (
        f", {weather.daylight_remaining_minutes} min daylight left"
        if weather.daylight_remaining_minutes > 0
        else ", dark"
    )
    return (
        f"{weather.weather_description}, {temp_str}, "
        f"{weather.wind_direction} {weather.wind_speed_kmh:.0f} km/h"
        f"{precip}{daylight}"
    )
