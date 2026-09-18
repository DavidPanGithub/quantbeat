"""SQLite persistence for precomputed game rounds.

A "round" is fully computed once by ``prep.py`` and stored here: the candles the
player sees (``visible``), the hidden candles revealed after a guess
(``future``), the ground-truth direction, and each bot's call. The API only ever
sends ``visible`` to the client until a guess is submitted, so the future can't
be sniffed from network traffic.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS rounds (
    id               INTEGER PRIMARY KEY,
    visible_json     TEXT NOT NULL,
    future_json      TEXT NOT NULL,
    start_close      REAL NOT NULL,
    future_close     REAL NOT NULL,
    actual_direction TEXT NOT NULL,
    bot_calls_json   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass
class Round:
    id: int
    visible: List[dict]
    future: List[dict]
    start_close: float
    future_close: float
    actual_direction: str
    bot_calls: Dict[str, str]


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
        "future_close, actual_direction, bot_calls_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            r.id,
            json.dumps(r.visible),
            json.dumps(r.future),
            r.start_close,
            r.future_close,
            r.actual_direction,
            json.dumps(r.bot_calls),
        ),
    )


def count_rounds(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM rounds").fetchone()["n"]


def random_round_id(conn: sqlite3.Connection) -> Optional[int]:
    row = conn.execute("SELECT id FROM rounds ORDER BY RANDOM() LIMIT 1").fetchone()
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
        future_close=row["future_close"],
        actual_direction=row["actual_direction"],
        bot_calls=json.loads(row["bot_calls_json"]),
    )
