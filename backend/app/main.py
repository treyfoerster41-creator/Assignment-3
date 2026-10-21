from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import model
from .crisis import contains_limited_crisis_phrase
from .database import initialize_database, managed_connection


ROOT = Path(__file__).resolve().parents[2]
PRACTICE_ID = "breathing-4-6"
PRACTICE_VERSION = "1.0"
PLANNED_DURATION_MS = 60_000
CRISIS_REPLY = (
    "This prototype cannot provide crisis support. The independent Crisis support "
    "panel includes official U.S. call, text, and chat options."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def default_database_path() -> Path:
    model.load_project_env()
    configured = os.getenv("STILL_DATABASE_PATH", "backend/data/still.db")
    path = Path(configured)
    return path if path.is_absolute() else ROOT / path


class SessionCreate(BaseModel):
    practice_id: Literal["breathing-4-6"] = PRACTICE_ID


class SessionUpdate(BaseModel):
    status: Literal["in_progress", "paused", "completed", "ended_early", "interrupted"]
    active_duration_ms: int = Field(ge=0, le=600_000)
    elapsed_duration_ms: int = Field(ge=0, le=3_600_000)
    cycles_completed: int = Field(ge=0, le=6)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = None


def create_app(
    database_path: str | Path | None = None,
    model_reply=None,
) -> FastAPI:
    db_path = Path(database_path) if database_path is not None else default_database_path()
    initialize_database(db_path)
    reply_function = model_reply or model.generate_reply
    app = FastAPI(title="Still Coursework Prototype", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def db_connection():
        return managed_connection(db_path)

    def conversation_or_create(connection: sqlite3.Connection, requested_id: str | None) -> str:
        if requested_id:
            row = connection.execute(
                "SELECT id FROM conversations WHERE id = ?", (requested_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            return requested_id
        conversation_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO conversations (id, created_at, updated_at) VALUES (?, ?, ?)",
            (conversation_id, now, now),
        )
        return conversation_id

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "Still"}

    @app.get("/api/info")
    def info() -> dict[str, object]:
        key, model_id = model.model_configuration()
        return {
            "prototype": True,
            "model_mode": "live" if key else "mock",
            "model_id": model_id,
            "practice_id": PRACTICE_ID,
            "practice_version": PRACTICE_VERSION,
            "planned_duration_seconds": 60,
            "live_model_key_present": bool(key),
        }

    @app.post("/api/sessions", status_code=201)
    def start_session(body: SessionCreate) -> dict[str, object]:
        session_id = str(uuid.uuid4())
        now = utc_now()
        with db_connection() as connection:
            connection.execute(
                """INSERT INTO exercise_sessions
                   (id, practice_id, script_version, status, started_at, updated_at)
                   VALUES (?, ?, ?, 'in_progress', ?, ?)""",
                (session_id, body.practice_id, PRACTICE_VERSION, now, now),
            )
        return {
            "id": session_id,
            "practice_id": body.practice_id,
            "script_version": PRACTICE_VERSION,
            "status": "in_progress",
            "started_at": now,
            "planned_duration_seconds": 60,
        }

    @app.patch("/api/sessions/{session_id}")
    def update_session(session_id: str, body: SessionUpdate) -> dict[str, object]:
        now = utc_now()
        finished_at = now if body.status in {"completed", "ended_early", "interrupted"} else None
        with db_connection() as connection:
            row = connection.execute(
                "SELECT id, status FROM exercise_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Exercise session not found.")
            if row["status"] in {"completed", "ended_early", "interrupted"}:
                raise HTTPException(status_code=409, detail="This exercise session has ended.")
            if body.status == "completed" and body.active_duration_ms < PLANNED_DURATION_MS:
                raise HTTPException(status_code=422, detail="The planned breathing sequence is not complete yet.")
            connection.execute(
                """UPDATE exercise_sessions SET status = ?, active_duration_ms = ?,
                   elapsed_duration_ms = ?, cycles_completed = ?, updated_at = ?, finished_at = ?
                   WHERE id = ?""",
                (
                    body.status,
                    body.active_duration_ms,
                    body.elapsed_duration_ms,
                    body.cycles_completed,
                    now,
                    finished_at,
                    session_id,
                ),
            )
        return {
            "id": session_id,
            "status": body.status,
            "active_duration_ms": body.active_duration_ms,
            "elapsed_duration_ms": body.elapsed_duration_ms,
            "cycles_completed": body.cycles_completed,
            "finished_at": finished_at,
        }

    @app.get("/api/history")
    def history() -> dict[str, list[dict[str, object]]]:
        with db_connection() as connection:
            sessions = [
                dict(row)
                for row in connection.execute(
                    """SELECT id, practice_id, script_version, status, active_duration_ms,
                              elapsed_duration_ms, cycles_completed, started_at, finished_at
                       FROM exercise_sessions ORDER BY started_at DESC LIMIT 100"""
                ).fetchall()
            ]
            conversations = [
                dict(row)
                for row in connection.execute(
                    """SELECT id, created_at, updated_at FROM conversations
                       ORDER BY updated_at DESC LIMIT 100"""
                ).fetchall()
            ]
            messages = [
                dict(row)
                for row in connection.execute(
                    """SELECT id, conversation_id, role, text, source, created_at
                       FROM messages ORDER BY created_at ASC LIMIT 500"""
                ).fetchall()
            ]
        return {"sessions": sessions, "conversations": conversations, "messages": messages}

    @app.delete("/api/history")
    def clear_history() -> dict[str, int]:
        with db_connection() as connection:
            message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            conversation_count = connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            session_count = connection.execute("SELECT COUNT(*) FROM exercise_sessions").fetchone()[0]
            connection.execute("DELETE FROM messages")
            connection.execute("DELETE FROM conversations")
            connection.execute("DELETE FROM exercise_sessions")
        return {
            "deleted_messages": message_count,
            "deleted_conversations": conversation_count,
            "deleted_sessions": session_count,
        }

    @app.post("/api/chat", status_code=201)
    async def chat(body: ChatRequest) -> dict[str, object]:
        if not body.message.strip():
            raise HTTPException(status_code=422, detail="Enter a short fictional example or leave this optional field blank.")

        crisis_match = contains_limited_crisis_phrase(body.message)
        now = utc_now()
        with db_connection() as connection:
            conversation_id = conversation_or_create(connection, body.conversation_id)
            if crisis_match:
                # The triggering text is deliberately neither persisted nor sent to a model.
                connection.execute(
                    "INSERT INTO messages (id, conversation_id, role, text, source, created_at) VALUES (?, ?, 'assistant', ?, 'fixed', ?)",
                    (str(uuid.uuid4()), conversation_id, "The app displayed its fixed Crisis support panel. No message text was stored.", now),
                )
                connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
                )
                return {
                    "conversation_id": conversation_id,
                    "reply": CRISIS_REPLY,
                    "source": "fixed",
                    "crisis_route": True,
                    "message_saved": False,
                    "notice": "A limited phrase rule matched. This is not a distress detector.",
                }

            recent_rows = connection.execute(
                """SELECT role, text FROM messages WHERE conversation_id = ?
                   ORDER BY created_at DESC LIMIT 6""",
                (conversation_id,),
            ).fetchall()
            recent_history = [dict(row) for row in reversed(recent_rows)]
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, text, source, created_at) VALUES (?, ?, 'user', ?, 'user', ?)",
                (str(uuid.uuid4()), conversation_id, body.message.strip(), now),
            )

        try:
            reply, source = await reply_function(body.message.strip(), recent_history)
        except Exception:
            # Keep provider errors out of the API response and stored conversation.
            reply, source = model.MODEL_FALLBACK_REPLY, "fallback"

        if not isinstance(reply, str) or not reply.strip():
            reply, source = model.MODEL_FALLBACK_REPLY, "fallback"
        reply = reply.strip()[:500]
        saved_at = utc_now()
        with db_connection() as connection:
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, text, source, created_at) VALUES (?, ?, 'assistant', ?, ?, ?)",
                (str(uuid.uuid4()), conversation_id, reply, source, saved_at),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (saved_at, conversation_id)
            )
        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "source": source,
            "crisis_route": False,
            "message_saved": True,
            "notice": (
                "Live Gemini response."
                if source == "gemini"
                else "Preset demo response; no live model was called."
                if source == "mock"
                else "The live model could not be reached; a fixed reply was shown."
            ),
        }

    return app


app = create_app()
