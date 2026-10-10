"""Trailhead - Local-first outdoor outing generator."""

from __future__ import annotations

__version__ = "0.1.0"

from trailhead.llm import OLLAMA_MODEL, check_ollama_health, generate_outing_card
from trailhead.models import (
    OUTING_CARD_JSON_SCHEMA,
    Activity,
    JournalEntry,
    Location,
    OutingCard,
    UserInput,
    WeatherData,
)
from trailhead.prompts import build_fallback_card, build_prompt
from trailhead.render import render_html, render_pdf, save_html
from trailhead.store import (
    add_entry,
    delete_entry,
    entry_count,
    get_entries,
    get_entry,
    init_db,
    update_entry_notes,
)
from trailhead.weather import fetch_weather, format_weather_summary, geocode_city

__all__ = [
    # Models
    "Activity",
    "WeatherData",
    "Location",
    "OutingCard",
    "UserInput",
    "JournalEntry",
    "OUTING_CARD_JSON_SCHEMA",
    # Weather
    "geocode_city",
    "fetch_weather",
    "format_weather_summary",
    # LLM
    "generate_outing_card",
    "check_ollama_health",
    "OLLAMA_MODEL",
    # Prompts
    "build_prompt",
    "build_fallback_card",
    # Render
    "render_html",
    "save_html",
    "render_pdf",
    # Store
    "init_db",
    "add_entry",
    "get_entries",
    "get_entry",
    "update_entry_notes",
    "delete_entry",
    "entry_count",
]
