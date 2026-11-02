from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .exercises import EXERCISE_IDS


_EXERCISE_IDS_SQL = ", ".join("'" + exercise_id.replace("'", "''") + "'" for exercise_id in EXERCISE_IDS)


SCHEMA = f"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 40),
    preferred_exercise_id TEXT CHECK (
        preferred_exercise_id IS NULL OR
        preferred_exercise_id IN ({_EXERCISE_IDS_SQL})
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    profile_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
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
    profile_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    practice_id TEXT NOT NULL CHECK (practice_id IN ({_EXERCISE_IDS_SQL})),
    script_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'paused', 'completed', 'ended_early', 'interrupted')),
    active_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (active_duration_ms >= 0),
    elapsed_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (elapsed_duration_ms >= 0),
    cycles_completed INTEGER NOT NULL DEFAULT 0 CHECK (cycles_completed >= 0),
    steps_completed INTEGER NOT NULL DEFAULT 0 CHECK (steps_completed >= 0),
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    exercise_id TEXT NOT NULL CHECK (exercise_id IN ({_EXERCISE_IDS_SQL})),
    source TEXT NOT NULL CHECK (source IN ('gemini', 'mock', 'fallback')),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_time
    ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_started
    ON exercise_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_profile_created
    ON recommendations(profile_id, created_at DESC);
"""


_MIGRATIONS = {
    "conversations": {
        "profile_id": "TEXT REFERENCES profiles(id) ON DELETE SET NULL",
    },
    "exercise_sessions": {
        "profile_id": "TEXT REFERENCES profiles(id) ON DELETE SET NULL",
        "steps_completed": "INTEGER NOT NULL DEFAULT 0 CHECK (steps_completed >= 0)",
    },
}


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


def _ensure_column(connection: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if name not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _table_sql(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return str(row[0] or "") if row else ""


def _rebuild_exercise_id_constraints(connection: sqlite3.Connection) -> None:
    tables = (
        ("profiles", "preferred_exercise_id"),
        ("exercise_sessions", "practice_id"),
        ("recommendations", "exercise_id"),
    )
    if (
        all(all(exercise_id in _table_sql(connection, table) for exercise_id in EXERCISE_IDS) for table, _ in tables)
        and "'fallback'" in _table_sql(connection, "recommendations")
    ):
        return

    # SQLite cannot alter a CHECK constraint. Rebuild only the three catalog-bound
    # tables, copying every row while foreign-key enforcement is paused.
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"""CREATE TABLE profiles_catalog_v4 (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 40),
            preferred_exercise_id TEXT CHECK (
                preferred_exercise_id IS NULL OR preferred_exercise_id IN ({_EXERCISE_IDS_SQL})
            ),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        connection.execute(
            """INSERT INTO profiles_catalog_v4
               (id, display_name, preferred_exercise_id, created_at, updated_at)
               SELECT id, display_name, preferred_exercise_id, created_at, updated_at FROM profiles"""
        )
        connection.execute(f"""CREATE TABLE exercise_sessions_catalog_v4 (
            id TEXT PRIMARY KEY,
            profile_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
            practice_id TEXT NOT NULL CHECK (practice_id IN ({_EXERCISE_IDS_SQL})),
            script_version TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('in_progress', 'paused', 'completed', 'ended_early', 'interrupted')),
            active_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (active_duration_ms >= 0),
            elapsed_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (elapsed_duration_ms >= 0),
            cycles_completed INTEGER NOT NULL DEFAULT 0 CHECK (cycles_completed >= 0),
            steps_completed INTEGER NOT NULL DEFAULT 0 CHECK (steps_completed >= 0),
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            finished_at TEXT
        )""")
        connection.execute(
            """INSERT INTO exercise_sessions_catalog_v4
               (id, profile_id, practice_id, script_version, status, active_duration_ms,
                elapsed_duration_ms, cycles_completed, steps_completed, started_at, updated_at, finished_at)
               SELECT id, profile_id, practice_id, script_version, status, active_duration_ms,
                      elapsed_duration_ms, cycles_completed, steps_completed, started_at, updated_at, finished_at
               FROM exercise_sessions"""
        )
        connection.execute(f"""CREATE TABLE recommendations_catalog_v4 (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
            exercise_id TEXT NOT NULL CHECK (exercise_id IN ({_EXERCISE_IDS_SQL})),
            source TEXT NOT NULL CHECK (source IN ('gemini', 'mock', 'fallback')),
            created_at TEXT NOT NULL
        )""")
        connection.execute(
            """INSERT INTO recommendations_catalog_v4
               (id, profile_id, conversation_id, exercise_id, source, created_at)
               SELECT id, profile_id, conversation_id, exercise_id, source, created_at FROM recommendations"""
        )

        connection.execute("DROP TABLE recommendations")
        connection.execute("DROP TABLE exercise_sessions")
        connection.execute("DROP TABLE profiles")
        connection.execute("ALTER TABLE profiles_catalog_v4 RENAME TO profiles")
        connection.execute("ALTER TABLE exercise_sessions_catalog_v4 RENAME TO exercise_sessions")
        connection.execute("ALTER TABLE recommendations_catalog_v4 RENAME TO recommendations")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started ON exercise_sessions(started_at DESC)")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_recommendations_profile_created "
            "ON recommendations(profile_id, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_profile_started "
            "ON exercise_sessions(profile_id, started_at DESC)"
        )
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError("catalog migration found a foreign-key violation")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


def initialize_database(database_path: str | Path) -> None:
    with managed_connection(database_path) as connection:
        connection.executescript(SCHEMA)
        for table, columns in _MIGRATIONS.items():
            for name, definition in columns.items():
                _ensure_column(connection, table, name, definition)
        _rebuild_exercise_id_constraints(connection)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_profile_started "
            "ON exercise_sessions(profile_id, started_at DESC)"
        )
