"""SQLite persistence for precomputed game rounds.

A "round" is computed once by ``prep.py``: the candles the player sees
(``visible``), the hidden candles for the *longest* horizon (``future``), the
reference close at the prediction point, each bot's directional call, and the
real calendar dates of the window (for era filtering and the post-guess reveal).
The API slices ``future`` to whatever horizon the player picks and scores
against that — the bots' calls don't depend on horizon, so one round serves
them all.

The API only ever sends ``visible`` and the hidden dates to the client after a
guess, so neither the future nor the window's dates can be sniffed beforehand.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS rounds (
    id             INTEGER PRIMARY KEY,
    visible_json   TEXT NOT NULL,
    future_json    TEXT NOT NULL,
    start_close    REAL NOT NULL,
    bot_calls_json TEXT NOT NULL,
    start_date     TEXT NOT NULL,
    end_date       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rounds_start_date ON rounds (start_date);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass
class Round:
    id: int
    visible: List[dict]
    future: List[dict]  # MAX_HORIZON bars
    start_close: float
    bot_calls: Dict[str, str]
    start_date: str  # real date at the prediction point
    end_date: str  # real date at the end of the longest horizon


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def reset_rounds(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM rounds")
    conn.commit()


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def insert_round(conn: sqlite3.Connection, r: Round) -> None:
    conn.execute(
        "INSERT INTO rounds (id, visible_json, future_json, start_close, "
        "bot_calls_json, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            r.id,
            json.dumps(r.visible),
            json.dumps(r.future),
            r.start_close,
            json.dumps(r.bot_calls),
            r.start_date,
            r.end_date,
        ),
    )


def count_rounds(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM rounds").fetchone()["n"]


def random_round_id(
    conn: sqlite3.Connection,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Optional[int]:
    """Pick a random round, optionally constrained to a prediction-point date
    range (inclusive). ISO dates compare correctly as strings."""
    clauses: List[str] = []
    params: List[str] = []
    if from_date:
        clauses.append("start_date >= ?")
        params.append(from_date)
    if to_date:
        clauses.append("start_date <= ?")
        params.append(to_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    row = conn.execute(
        f"SELECT id FROM rounds {where} ORDER BY RANDOM() LIMIT 1", params
    ).fetchone()
    return row["id"] if row else None


def get_round(conn: sqlite3.Connection, round_id: int) -> Optional[Round]:
    row = conn.execute("SELECT * FROM rounds WHERE id = ?", (round_id,)).fetchone()
    if row is None:
        return None
    return Round(
        id=row["id"],
        visible=json.loads(row["visible_json"]),
        future=json.loads(row["future_json"]),
        start_close=row["start_close"],
        bot_calls=json.loads(row["bot_calls_json"]),
        start_date=row["start_date"],
        end_date=row["end_date"],
    )
