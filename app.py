"""Trailhead - Turn a few taps into a short outdoor outing."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from trailhead import (
    OLLAMA_MODEL,
    Activity,
    OutingCard,
    UserInput,
    add_entry,
    check_ollama_health,
    delete_entry,
    entry_count,
    fetch_weather,
    generate_outing_card,
    geocode_city,
    get_entries,
    init_db,
    render_html,
    render_pdf,
)

# Page config
st.set_page_config(
    page_title="Trailhead",
    page_icon="🌲",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "card" not in st.session_state:
    st.session_state.card = None
if "weather" not in st.session_state:
    st.session_state.weather = None
if "location" not in st.session_state:
    st.session_state.location = None
if "show_outside_screen" not in st.session_state:
    st.session_state.show_outside_screen = False
if "outside_return_time" not in st.session_state:
    st.session_state.outside_return_time = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "using_fallback" not in st.session_state:
    st.session_state.using_fallback = False


def reset_flow() -> None:
    """Reset the app to initial state."""
    st.session_state.card = None
    st.session_state.weather = None
    st.session_state.location = None
    st.session_state.show_outside_screen = False
    st.session_state.outside_return_time = None
    st.session_state.error_message = None
    st.session_state.using_fallback = False


def render_sidebar() -> None:
    """Render sidebar with status and controls."""
    with st.sidebar:
        st.markdown("### 🌲 Trailhead")
        st.caption("Local-first. Your data stays on device.")

        # Ollama status
        healthy, version, models = check_ollama_health()
        if healthy:
            st.success(f"Ollama running • {OLLAMA_MODEL}", icon="✅")
        else:
            st.error("Ollama not reachable or model missing", icon="❌")
            st.markdown(f"""
**Setup:**
```bash
ollama serve
ollama pull {OLLAMA_MODEL}
```
Then reload the app.
""")
            st.session_state.using_fallback = True

        st.divider()

        # Journal stats
        count = entry_count()
        st.metric("Journal entries", count)

        if st.button("Clear journal", type="secondary", use_container_width=True):
            # Delete the database file
            db_path = Path("trailhead_journal.sqlite")
            if db_path.exists():
                db_path.unlink()
            st.rerun()

        st.divider()
        st.caption(f"Model: `{OLLAMA_MODEL}`")
        st.caption("Set `OLLAMA_MODEL` env var to change")


def render_form() -> UserInput | None:
    """Render the input form. Returns UserInput on submit, None otherwise."""
    with st.form("outing_form", border=True):
        st.markdown("#### Where and what?")

        col1, col2 = st.columns(2)
        with col1:
            activity = st.selectbox(
                "Activity",
                options=list(Activity),
                format_func=lambda a: a.label,
                index=0,
            )
        with col2:
            time_minutes = st.select_slider(
                "Time available",
                options=[15, 30, 45, 60, 90, 120, 150, 180],
                value=45,
                format_func=lambda m: (
                    f"{m} min" if m < 60 else f"{m//60}h" if m % 60 == 0 else f"{m//60}h {m%60}m"
                ),
            )

        st.markdown("#### Location")
        loc_method = st.radio(
            "How to specify location?",
            ["City name (geocode)", "Manual lat/lon"],
            horizontal=True,
        )

        location_name = ""
        latitude = None
        longitude = None

        if loc_method == "City name (geocode)":
            location_name = st.text_input(
                "City / Town",
                placeholder="e.g., Portland, IL or Seattle",
                help="Uses Open-Meteo's free geocoding API",
            )
        else:
            col1, col2 = st.columns(2)
            with col1:
                latitude = st.number_input(
                    "Latitude", value=47.6062, format="%.6f", min_value=-90.0, max_value=90.0
                )
            with col2:
                longitude = st.number_input(
                    "Longitude", value=-122.3321, format="%.6f", min_value=-180.0, max_value=180.0
                )
            location_name = f"{latitude:.4f}, {longitude:.4f}"

        submitted = st.form_submit_button(
            "Generate outing card",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get("generating", False),
        )

        if submitted:
            if loc_method == "City name (geocode)" and not location_name.strip():
                st.error("Please enter a city name")
                return None

            return UserInput(
                activity=activity,
                time_available_minutes=time_minutes,
                location_name=location_name.strip(),
                latitude=latitude,
                longitude=longitude,
            )

    return None


def fetch_location_and_weather(user_input: UserInput) -> tuple[bool, str | None]:
    """Fetch location (if needed) and weather. Returns (success, error_message)."""
    # Resolve location
    if user_input.has_coordinates():
        from trailhead.models import Location
        location = Location(
            name=user_input.location_name,
            latitude=user_input.latitude,
            longitude=user_input.longitude,
            timezone="UTC",  # Will be overridden by weather call
        )
    else:
        with st.spinner("Finding location..."):
            location = geocode_city(user_input.location_name)
        if location is None:
            return False, f"Could not find location: {user_input.location_name}"

    st.session_state.location = location

    # Fetch weather
    with st.spinner("Fetching weather..."):
        weather = fetch_weather(location.latitude, location.longitude, location.timezone)

    if weather is None:
        return False, "Failed to fetch weather. Check your connection."

    st.session_state.weather = weather
    return True, None


def generate_card(user_input: UserInput) -> None:
    """Generate the outing card."""
    st.session_state.generating = True
    try:
        with st.spinner("Generating your outing card..."):
            card, error = generate_outing_card(
                activity=user_input.activity,
                location_name=st.session_state.location.name,
                latitude=st.session_state.location.latitude,
                longitude=st.session_state.location.longitude,
                time_minutes=user_input.time_available_minutes,
                weather=st.session_state.weather,
            )

        if card is None:
            st.session_state.error_message = error or "Failed to generate card"
        else:
            st.session_state.card = card
            st.session_state.using_fallback = error is not None
            if error:
                st.session_state.error_message = error
    finally:
        st.session_state.generating = False
    st.rerun()


def render_card(card: OutingCard) -> None:
    """Render the outing card with download buttons and 'Take me outside'."""
    # Error/warning banner
    if st.session_state.using_fallback:
        msg = st.session_state.error_message or "Using fallback card (Ollama unavailable)"
        st.warning(msg, icon="⚠️")
    elif st.session_state.error_message:
        st.error(st.session_state.error_message, icon="❌")

    # Card display
    with st.container(border=True):
        # Header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {card.activity.label} at {card.location_name}")
            ts = format_timestamp(card.generated_at)
            st.caption(f"{card.time_available_minutes} minutes • Generated {ts}")
        with col2:
            st.markdown(f"**Weather:** {card.weather_summary}")

        st.divider()

        # Route
        st.markdown("#### 🗺️ Route")
        st.markdown(card.route_suggestion)

        # Seasonal highlights
        st.markdown("#### 🍂 Seasonal Highlights")
        st.markdown(card.seasonal_highlights)

        # Challenges
        st.markdown("#### 📵 Off-Screen Challenges")
        for i, challenge in enumerate(card.off_screen_challenges, 1):
            st.markdown(f"**{i}.** {challenge}")

        # Safety
        st.markdown("#### ⚠️ Safety")
        st.warning(card.safety_note, icon="⚠️")

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📄 Download HTML", use_container_width=True):
            html = render_html(card)
            now = datetime.now().strftime("%Y%m%d")
            loc = card.location_name.replace(" ", "_")
            fname = f"trailhead_{card.activity.value}_{loc}_{now}.html"
            st.download_button(
                "Save HTML file",
                data=html,
                file_name=fname,
                mime="text/html",
                use_container_width=True,
            )

    with col2:
        if st.button("📑 Download PDF", use_container_width=True):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                render_pdf(card, tmp.name)
                with open(tmp.name, "rb") as f:
                    pdf_data = f.read()
            now = datetime.now().strftime("%Y%m%d")
            loc = card.location_name.replace(" ", "_")
            fname = f"trailhead_{card.activity.value}_{loc}_{now}.pdf"
            st.download_button(
                "Save PDF file",
                data=pdf_data,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
            )

    with col3:
        if st.button("🚪 Take me outside", type="primary", use_container_width=True):
            st.session_state.show_outside_screen = True
            # Calculate return time
            from datetime import timedelta
            return_time = datetime.now() + timedelta(minutes=card.time_available_minutes)
            st.session_state.outside_return_time = return_time
            st.rerun()


def format_timestamp(iso_str: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except Exception:
        return iso_str


def render_outside_screen() -> None:
    """Render the 'Take me outside' minimal screen."""
    return_time = st.session_state.outside_return_time
    if return_time is None:
        return

    minutes_left = int((return_time - datetime.now()).total_seconds() / 60)
    minutes_left = max(0, minutes_left)

    # Big minimal screen
    st.markdown(
        f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 60vh;
            text-align: center;
            color: #1B5E20;
        ">
            <h1 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 700;">🌲</h1>
            <h2 style="font-size: 2rem; margin-bottom: 0.5rem;">
                See you in {minutes_left} minutes
            </h2>
            <p style="font-size: 1.2rem; color: #555; max-width: 400px;">
                Your outing card is saved. Put the phone away.
                Notice the air, the sounds, the light.
            </p>
            <p style="font-size: 1rem; color: #888; margin-top: 1.5rem;">
                Return by {return_time.strftime('%I:%M %p')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← Back to Trailhead", use_container_width=True):
        st.session_state.show_outside_screen = False
        st.session_state.outside_return_time = None
        st.rerun()


def render_journal_tab() -> None:
    """Render the journal tab with past entries."""
    st.markdown("### 📓 After the walk")

    # Add new entry form (if there's a current card)
    if st.session_state.card is not None:
        with st.expander("Save current outing to journal", expanded=False):
            notes = st.text_area(
                "Quick notes (1-3 lines)",
                placeholder="What did you notice? How did it feel? Anything unexpected?",
                max_chars=500,
                height=100,
            )
            if st.button("Save to journal", type="primary"):
                entry_id = add_entry(st.session_state.card, notes)
                st.success(f"Saved as entry #{entry_id}")
                st.rerun()

    st.divider()

    # List entries
    entries = get_entries(limit=20)
    if not entries:
        st.info("No journal entries yet. Complete an outing and save it!")
        return

    for entry in entries:
        card = entry.card
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                label = f"{card.activity.label} at {card.location_name}"
                st.markdown(f"**{label}** — {card.time_available_minutes} min")
                st.caption(f"{format_timestamp(entry.created_at)}")
                if entry.notes:
                    st.markdown(f"*\"{entry.notes}\"*")
            with col2:
                if st.button("🗑️", key=f"del_{entry.id}", help="Delete entry"):
                    delete_entry(entry.id)
                    st.rerun()


def main():
    render_sidebar()

    # Main tabs
    tab1, tab2 = st.tabs(["🌲 New Outing", "📓 Journal"])

    with tab1:
        if st.session_state.show_outside_screen:
            render_outside_screen()
        elif st.session_state.card is not None:
            render_card(st.session_state.card)
            if st.button("← New outing", use_container_width=True):
                reset_flow()
                st.rerun()
        else:
            st.markdown("# 🌲 Trailhead")
            st.markdown(
                "Turn a few taps into a short outdoor outing. "
                "Spend under 60 seconds here, then go outside."
            )
            st.divider()

            user_input = render_form()
            if user_input:
                success, error = fetch_location_and_weather(user_input)
                if not success:
                    st.error(error, icon="❌")
                else:
                    generate_card(user_input)

    with tab2:
        render_journal_tab()


if __name__ == "__main__":
    # Initialize DB on startup
    init_db()
    main()
