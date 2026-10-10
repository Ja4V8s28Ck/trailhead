"""Prompt templates for the outing card generation."""

from __future__ import annotations

from datetime import datetime

from trailhead.models import OUTING_CARD_JSON_SCHEMA, Activity, WeatherData

SYSTEM_PROMPT = (
    "You are a concise outdoor guide. Generate a practical outing card for "
    "someone who wants to spend a short time outside. Be specific to the "
    "location, season, weather, and activity. No fluff, no fake map data, "
    "no invented trail names. Keep it actionable and grounded in what's "
    "actually observable."
)

USER_PROMPT_TEMPLATE = (
    "Create an outing card for:\n"
    "- Activity: {activity}\n"
    "- Location: {location_name} (lat {latitude:.3f}, lon {longitude:.3f})\n"
    "- Time available: {time_minutes} minutes\n"
    "- Current weather: {weather_summary}\n"
    "- Sunrise: {sunrise}, Sunset: {sunset}\n"
    "- Daylight remaining: {daylight_minutes} minutes\n"
    "- Season: {season} (Northern Hemisphere)\n\n"
    "Return JSON matching this schema:\n"
    "{json_schema}\n\n"
    "Guidelines:\n"
    "1. route_suggestion: General only (e.g., \"loop through the nearest park, "
    "turn around at 25 min\"). No fake trail names, no specific coordinates, "
    "no map data.\n"
    "2. seasonal_highlights: What to look and listen for THIS WEEK at THIS "
    "LATITUDE in THIS SEASON. Be specific to hemisphere and time of year "
    "(e.g., migrating warblers, fall colors, frog calls, specific tree "
    "species flowering).\n"
    "3. off_screen_challenges: Exactly 3 concrete, doable challenges that "
    "get the user OFF the screen. Examples: \"Sit silently 3 minutes and "
    "count distinct sounds\", \"Find 5 different leaf shapes\", \"Spot a bird "
    "and watch it until it flies away\". No phone use.\n"
    "4. safety_note: One line, grounded in the actual weather and daylight. "
    'E.g., "Thunderstorm risk — turn back at first thunder" or "Dark in 40 '
    'min — bring a headlamp or turn around by 6:20pm".\n'
    "5. weather_summary: Brief human-readable summary for display (reuse the "
    "input summary)."
)


def build_prompt(
    activity: Activity,
    location_name: str,
    latitude: float,
    longitude: float,
    time_minutes: int,
    weather: WeatherData,
) -> str:
    """Build the user prompt with all context filled in."""
    # Determine season (Northern Hemisphere)
    month = datetime.now().month
    if 3 <= month <= 5:
        season = "spring"
    elif 6 <= month <= 8:
        season = "summer"
    elif 9 <= month <= 11:
        season = "autumn"
    else:
        season = "winter"

    return USER_PROMPT_TEMPLATE.format(
        activity=activity.value,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        time_minutes=time_minutes,
        weather_summary=weather.weather_description,
        sunrise=weather.sunrise,
        sunset=weather.sunset,
        daylight_minutes=weather.daylight_remaining_minutes,
        season=season,
        json_schema=OUTING_CARD_JSON_SCHEMA,
    )


# Fallback template card for offline/fallback mode
FALLBACK_CARD_TEMPLATE = (
    "{{activity}} outing at {{location_name}} — {{time_minutes}} minutes\n\n"
    "Route: Loop through the nearest green space, turn around at the "
    "halfway mark.\n\n"
    "Seasonal highlights: It's {{season}} in the Northern Hemisphere. Look "
    "for seasonal changes appropriate to your latitude — migratory birds, "
    "flowering plants, changing leaves, or winter residents.\n\n"
    "Off-screen challenges:\n"
    "1. Sit silently for 3 minutes and count every distinct sound you hear.\n"
    "2. Find 5 different textures (bark, leaf, stone, grass, water) and "
    "notice each.\n"
    "3. Pick one tree or plant and observe it closely for 2 minutes — "
    "notice details you'd miss at a glance.\n\n"
    "Safety: {{safety_note}}\n\n"
    "Generated: {{generated_at}}\n"
    "Weather: {{weather_summary}}"
)


def build_fallback_card(
    activity: Activity,
    location_name: str,
    time_minutes: int,
    weather: WeatherData,
) -> str:
    """Build a simple fallback card when Ollama is unavailable."""
    month = datetime.now().month
    if 3 <= month <= 5:
        season = "spring"
    elif 6 <= month <= 8:
        season = "summer"
    elif 9 <= month <= 11:
        season = "autumn"
    else:
        season = "winter"

    # Simple safety note based on conditions
    if weather.weather_code in (95, 96, 99):
        safety = "Thunderstorm risk — seek shelter immediately"
    elif weather.daylight_remaining_minutes < 30:
        safety = f"Dark in {weather.daylight_remaining_minutes} min — bring light or head back now"
    elif weather.precipitation_mm > 5:
        safety = "Heavy rain — wear waterproof layers, watch for slippery ground"
    elif weather.temperature_c < 0:
        safety = "Below freezing — dress in layers, watch for ice"
    elif weather.temperature_c > 30:
        safety = "Hot — bring water, seek shade, watch for heat exhaustion"
    else:
        safety = "Conditions look good — stay aware of changing weather"

    return FALLBACK_CARD_TEMPLATE.format(
        activity=activity.label,
        location_name=location_name,
        time_minutes=time_minutes,
        season=season,
        safety_note=safety,
        generated_at=datetime.now().isoformat(),
        weather_summary=format_weather_summary(weather),
    )


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
