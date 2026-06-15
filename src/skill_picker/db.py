"""SQLite connection + schema for the skill pool and vector cache.

A single SQLite file holds both skills and their cached embedding vectors — no server,
no deployment, just a file (the reason SQLite was chosen for this project).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    match_text       TEXT NOT NULL,
    full_description TEXT NOT NULL,
    tags             TEXT NOT NULL DEFAULT '[]',
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vectors (
    skill_id    TEXT PRIMARY KEY REFERENCES skills(id) ON DELETE CASCADE,
    signature   TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    dim         INTEGER NOT NULL,
    vector      BLOB NOT NULL
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite database and ensure the schema exists."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI serves sync handlers from a threadpool; WAL mode
    # keeps concurrent reads safe and serializes writes for this single-process service.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
