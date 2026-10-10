"""Ollama client for structured outing card generation."""

from __future__ import annotations

import json
import os
from datetime import datetime

import ollama
from pydantic import ValidationError

from trailhead.models import (
    OUTING_CARD_JSON_SCHEMA,
    Activity,
    OutingCard,
    WeatherData,
)
from trailhead.prompts import build_fallback_card, build_prompt, format_weather_summary

DEFAULT_MODEL = "gemma3:4b"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)


class OllamaUnavailableError(Exception):
    """Raised when Ollama cannot be reached or model is not available."""
    pass


def _ollama_client() -> ollama.Client:
    """Create Ollama client with default host."""
    return ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))


def check_ollama_health() -> tuple[bool, str, list[str]]:
    """
    Check if Ollama is reachable and the model is available.
    Returns (is_healthy, version, available_models).
    """
    try:
        client = _ollama_client()
        # List models to check connectivity
        models_resp = client.list()
        version = "unknown"
        available = []

        # ollama-python returns a ListResponse with models attribute
        if hasattr(models_resp, 'models'):
            for m in models_resp.models:
                name = getattr(m, 'model', getattr(m, 'name', str(m)))
                available.append(name)
        elif isinstance(models_resp, dict) and 'models' in models_resp:
            for m in models_resp['models']:
                name = m.get('name', m.get('model', str(m)))
                available.append(name)

        # Try to get version from show
        try:
            show_resp = client.show(OLLAMA_MODEL)
            if hasattr(show_resp, "model_info"):
                version = getattr(show_resp, "model_info", {}).get("version", "unknown")
            else:
                version = "unknown"
        except Exception:
            pass

        model_available = OLLAMA_MODEL in available
        if not model_available:
            return False, version, available

        return True, version, available
    except Exception as e:
        return False, str(e), []


def generate_outing_card(
    activity: Activity,
    location_name: str,
    latitude: float,
    longitude: float,
    time_minutes: int,
    weather: WeatherData,
    max_retries: int = 1,
) -> tuple[OutingCard | None, str | None]:
    """
    Generate an outing card using Ollama with structured output.
    Returns (card, error_message). On failure, returns (None, error).
    Falls back to template card if Ollama unavailable.
    """
    client = _ollama_client()
    prompt = build_prompt(activity, location_name, latitude, longitude, time_minutes, weather)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise outdoor guide. "
                            "Generate a practical outing card. Return only valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                format=OUTING_CARD_JSON_SCHEMA,
                options={"temperature": 0.3},
            )

            content = response.message.content
            data = json.loads(content)

            # Ensure generated_at is present
            if "generated_at" not in data:
                data["generated_at"] = datetime.now().isoformat()

            # Ensure weather_summary is present
            if "weather_summary" not in data:
                data["weather_summary"] = format_weather_summary(weather)

            card = OutingCard(**data)
            return card, None

        except (json.JSONDecodeError, ValidationError) as e:
            last_error = f"Validation error (attempt {attempt + 1}): {e}"
            if attempt == max_retries:
                break
        except ollama.ResponseError as e:
            last_error = f"Ollama error: {e.error}"
            break
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            break

    # All retries failed - return fallback
    build_fallback_card(activity, location_name, time_minutes, weather)
    # Create a minimal OutingCard from fallback for consistency
    fallback_card = OutingCard(
        activity=activity,
        location_name=location_name,
        time_available_minutes=time_minutes,
        route_suggestion=(
            "Loop through the nearest green space, turn around at the halfway mark."
        ),
        seasonal_highlights=(
            f"It's {_current_season()} in the Northern Hemisphere. "
            "Observe seasonal changes at your latitude."
        ),
        off_screen_challenges=[
            "Sit silently for 3 minutes and count every distinct sound you hear.",
            "Find 5 different textures (bark, leaf, stone, grass, water) and notice each.",
            "Pick one tree or plant and observe it closely for 2 minutes.",
        ],
        safety_note=_fallback_safety(weather),
        generated_at=datetime.now().isoformat(),
        weather_summary=format_weather_summary(weather),
    )
    return fallback_card, f"Ollama unavailable ({last_error}). Using fallback card."


def _current_season() -> str:
    month = datetime.now().month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    return "winter"


def _fallback_safety(weather: WeatherData) -> str:
    if weather.weather_code in (95, 96, 99):
        return "Thunderstorm risk — seek shelter immediately"
    elif weather.daylight_remaining_minutes < 30:
        return f"Dark in {weather.daylight_remaining_minutes} min — bring light or head back now"
    elif weather.precipitation_mm > 5:
        return "Heavy rain — wear waterproof layers, watch for slippery ground"
    elif weather.temperature_c < 0:
        return "Below freezing — dress in layers, watch for ice"
    elif weather.temperature_c > 30:
        return "Hot — bring water, seek shade, watch for heat exhaustion"
    return "Conditions look good — stay aware of changing weather"
