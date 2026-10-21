from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    text TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('user', 'gemini', 'mock', 'fallback', 'fixed')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exercise_sessions (
    id TEXT PRIMARY KEY,
    practice_id TEXT NOT NULL,
    script_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'paused', 'completed', 'ended_early', 'interrupted')),
    active_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (active_duration_ms >= 0),
    elapsed_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (elapsed_duration_ms >= 0),
    cycles_completed INTEGER NOT NULL DEFAULT 0 CHECK (cycles_completed >= 0),
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_time
    ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_started
    ON exercise_sessions(started_at DESC);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def managed_connection(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: str | Path) -> None:
    with managed_connection(database_path) as connection:
        connection.executescript(SCHEMA)
