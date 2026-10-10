"""SQLite storage for journal entries."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from trailhead.models import Activity, JournalEntry, OutingCard

DB_PATH = Path("trailhead_journal.sqlite")


SCHEMA = """
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_json TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_journal_created_at ON journal_entries(created_at DESC);
"""


def init_db() -> None:
    """Initialize the database schema."""
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def _connect():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _card_to_json(card: OutingCard) -> str:
    """Serialize OutingCard to JSON string."""
    return card.model_dump_json()


def _json_to_card(json_str: str) -> OutingCard:
    """Deserialize OutingCard from JSON string."""
    data = json.loads(json_str)
    # Handle activity enum
    if isinstance(data.get("activity"), str):
        data["activity"] = Activity(data["activity"])
    return OutingCard(**data)


def add_entry(card: OutingCard, notes: str = "") -> int:
    """Add a journal entry. Returns the new entry ID."""
    init_db()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO journal_entries (card_json, notes, created_at) VALUES (?, ?, ?)",
            (_card_to_json(card), notes, datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid


def get_entries(limit: int = 50, offset: int = 0) -> list[JournalEntry]:
    """Get journal entries, newest first."""
    init_db()
    query = (
        "SELECT id, card_json, notes, created_at FROM journal_entries "
        "ORDER BY created_at DESC LIMIT ? OFFSET ?"
    )
    with _connect() as conn:
        rows = conn.execute(query, (limit, offset)).fetchall()
        return [
            JournalEntry(
                id=row["id"],
                card=_json_to_card(row["card_json"]),
                notes=row["notes"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


def get_entry(entry_id: int) -> JournalEntry | None:
    """Get a single journal entry by ID."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, card_json, notes, created_at FROM journal_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            return None
        return JournalEntry(
            id=row["id"],
            card=_json_to_card(row["card_json"]),
            notes=row["notes"],
            created_at=row["created_at"],
        )


def update_entry_notes(entry_id: int, notes: str) -> bool:
    """Update notes for an entry. Returns True if updated."""
    init_db()
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE journal_entries SET notes = ? WHERE id = ?",
            (notes, entry_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_entry(entry_id: int) -> bool:
    """Delete a journal entry. Returns True if deleted."""
    init_db()
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0


def entry_count() -> int:
    """Get total number of journal entries."""
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM journal_entries").fetchone()
        return row["count"] if row else 0
