"""Pydantic models for Trailhead."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Activity(StrEnum):
    """Supported outdoor activities."""

    WALK = "walk"
    RUN = "run"
    HIKE = "hike"
    BIRDING = "birding"
    NATURE_OBSERVATION = "nature_observation"
    PHOTOGRAPHY = "photography"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


class WeatherData(BaseModel):
    """Current weather conditions from Open-Meteo."""

    temperature_c: float = Field(..., description="Current temperature in Celsius")
    temperature_f: float = Field(..., description="Current temperature in Fahrenheit")
    wind_speed_kmh: float = Field(..., description="Wind speed in km/h")
    wind_direction: str = Field(..., description="Wind direction (e.g., 'NW')")
    weather_code: int = Field(..., description="WMO weather code")
    weather_description: str = Field(..., description="Human-readable weather description")
    precipitation_mm: float = Field(..., description="Precipitation in mm")
    relative_humidity: int = Field(..., description="Relative humidity percentage")
    sunrise: str = Field(..., description="Sunrise time (ISO format)")
    sunset: str = Field(..., description="Sunset time (ISO format)")
    daylight_remaining_minutes: int = Field(..., description="Minutes of daylight remaining")
    is_daylight: bool = Field(..., description="Whether it's currently daylight")


class Location(BaseModel):
    """Geocoded location."""

    name: str = Field(..., description="City/location name")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timezone: str = Field(..., description="IANA timezone identifier")


class OutingCard(BaseModel):
    """The generated outing card with all details."""

    activity: Activity
    location_name: str
    time_available_minutes: int
    route_suggestion: str = Field(
        ...,
        description=(
            "General route suggestion, e.g., 'loop through nearest park, "
            "turn around at 25 min'"
        ),
    )
    seasonal_highlights: str = Field(
        ...,
        description="What to look and listen for this week at this latitude and season",
    )
    off_screen_challenges: list[str] = Field(
        ..., min_length=3, max_length=3, description="Three off-screen challenges"
    )
    safety_note: str = Field(
        ..., description="One-line safety note based on weather and daylight"
    )
    generated_at: str = Field(..., description="ISO timestamp when card was generated")
    weather_summary: str = Field(..., description="Brief weather summary for display")


class UserInput(BaseModel):
    """User input from the form."""

    activity: Activity
    time_available_minutes: int = Field(..., ge=15, le=180)
    location_name: str = Field(default="", description="City name for geocoding")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class JournalEntry(BaseModel):
    """A journal entry stored after the walk."""

    id: int | None = None
    card: OutingCard
    notes: str = Field(default="", description="User's 1-3 notes after the walk")
    created_at: str = Field(..., description="ISO timestamp when entry was created")


# JSON Schema for Ollama structured output
OUTING_CARD_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "activity": {"type": "string", "enum": [a.value for a in Activity]},
        "location_name": {"type": "string"},
        "time_available_minutes": {"type": "integer", "minimum": 15, "maximum": 180},
        "route_suggestion": {"type": "string"},
        "seasonal_highlights": {"type": "string"},
        "off_screen_challenges": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
        "safety_note": {"type": "string"},
        "generated_at": {"type": "string", "format": "date-time"},
        "weather_summary": {"type": "string"},
    },
    "required": [
        "activity",
        "location_name",
        "time_available_minutes",
        "route_suggestion",
        "seasonal_highlights",
        "off_screen_challenges",
        "safety_note",
        "generated_at",
        "weather_summary",
    ],
    "additionalProperties": False,
}
