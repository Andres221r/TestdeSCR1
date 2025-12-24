import sqlite3
from pathlib import Path
from typing import Iterable, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at TEXT NOT NULL,
    universe_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    visits INTEGER NOT NULL,
    playing INTEGER NOT NULL,
    favorites INTEGER NOT NULL,
    up_votes INTEGER NOT NULL,
    down_votes INTEGER NOT NULL,
    version TEXT
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_visits INTEGER NOT NULL,
    achieved_at TEXT,
    predicted_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    detected_at TEXT NOT NULL
);
"""


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def execute(db_path: str, query: str, params: Iterable = ()) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(query, params)
        conn.commit()


def fetchone(db_path: str, query: str, params: Iterable = ()) -> Optional[sqlite3.Row]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        return cur.fetchone()


def fetchall(db_path: str, query: str, params: Iterable = ()) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        return cur.fetchall()
