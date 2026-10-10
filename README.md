# Trailhead

A local-first Streamlit app that uses an open-weight LLM to turn a few taps into a short outdoor outing, then gets you **off the screen**.

## What it does

1. **Pick your outing** — Activity (walk, run, hike, birding, nature observation, photography), time (15 min – 3 hrs), and location (city name or lat/lon)
2. **Get conditions** — Fetches live weather, sunrise/sunset, and daylight remaining from Open-Meteo (free, no API key)
3. **Generate a card** — A locally running open-weight model (Gemma 3 4B via Ollama) creates an "outing card" with:
   - A general route suggestion (no fake map data)
   - What to look and listen for **this week at your latitude and season**
   - 3 "off-screen challenges" (e.g., "Sit silently 3 minutes and count the sounds you hear")
   - A one-line safety note based on actual weather and daylight
4. **Go outside** — Download the card as HTML or PDF, or tap **"Take me outside"** for a minimal screen showing your return time
5. **Journal it** — After the walk, add 1–3 notes. Stored locally in SQLite. Past cards stay readable offline.

## Why open models?

- **Offline** — Works without internet (except weather fetch; cached/past cards still open)
- **Private** — Your location, habits, and notes never leave your device
- **Swappable** — Change models via `OLLAMA_MODEL` env var; fine-tune your own
- **Zero per-request cost** — No API keys, no billing, no rate limits

## Quickstart

```bash
# 1. Create and activate virtual environment (Python 3.15)
py -3.15 -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull the model and start Ollama
ollama pull gemma3:4b
ollama serve  # In a separate terminal

# 4. Run Trailhead
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

### Swapping models

Set the `OLLAMA_MODEL` environment variable before running:

```bash
# Windows PowerShell
$env:OLLAMA_MODEL="llama3.2:3b"
streamlit run app.py

# macOS/Linux
OLLAMA_MODEL=qwen3:4b streamlit run app.py
```

Any chat-capable model pulled in Ollama works. Smaller models are faster; larger ones give richer seasonal highlights.

## What works offline

| Feature | Offline? |
|---------|----------|
| Generate outing card (with Ollama running) | ✅ Yes |
| View past journal entries | ✅ Yes |
| View cached weather (5 min TTL) | ⚠️ Partial |
| Fetch fresh weather | ❌ Needs internet |
| Pull new models | ❌ Needs internet |

## Project structure

```
trailhead/
├── app.py                    # Streamlit UI only
├── trailhead/
│   ├── __init__.py
│   ├── models.py             # Pydantic models + JSON schema
│   ├── weather.py            # Open-Meteo geocoding + weather
│   ├── llm.py                # Ollama structured output + fallback
│   ├── prompts.py            # Prompt templates
│   ├── render.py             # HTML + PDF (fpdf2) rendering
│   └── store.py              # SQLite journal storage
├── requirements.txt
├── pyproject.toml            # Ruff config
├── .streamlit/config.toml    # Theme + no telemetry
├── .gitignore
├── LICENSE
└── README.md
```

## Dependencies

Minimal, pinned in `requirements.txt`:
- `streamlit` — UI
- `httpx` — HTTP client for Open-Meteo
- `ollama` — Official Python client for structured output
- `pydantic` — Validation + JSON schema
- `fpdf2` — Pure-Python PDF generation
- `python-dotenv` — Env var loading

## Configuration

- `.streamlit/config.toml` — Disables Streamlit usage stats, sets green theme
- `OLLAMA_MODEL` env var — Default `gemma3:4b`
- `OLLAMA_HOST` env var — Default `http://localhost:11434`

## License

MIT — see [LICENSE](LICENSE).