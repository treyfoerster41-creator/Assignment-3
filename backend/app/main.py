from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from . import model
from .crisis import contains_limited_crisis_phrase
from .database import initialize_database, managed_connection
from .exercises import (
    BREATHING_ID,
    CYCLE_COUNT_LIMIT,
    EXERCISES,
    EXERCISE_IDS,
    STEP_COUNT_LIMIT,
    exercise_summary,
)


ROOT = Path(__file__).resolve().parents[2]
PRACTICE_ID = BREATHING_ID
PLANNED_DURATION_MS = {
    exercise_id: int(exercise["duration_seconds"]) * 1000
    for exercise_id, exercise in EXERCISES.items()
}
MAX_BREATHING_CYCLES = CYCLE_COUNT_LIMIT
MAX_STEP_COUNT = STEP_COUNT_LIMIT
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
    practice_id: str = PRACTICE_ID
    profile_id: str | None = None

    @field_validator("practice_id")
    @classmethod
    def fixed_exercise_only(cls, value: str) -> str:
        if value not in EXERCISE_IDS:
            raise ValueError("Choose one of the app's fixed practices.")
        return value


class SessionUpdate(BaseModel):
    status: Literal["in_progress", "paused", "completed", "ended_early", "interrupted"]
    active_duration_ms: int = Field(ge=0, le=600_000)
    elapsed_duration_ms: int = Field(ge=0, le=3_600_000)
    cycles_completed: int = Field(ge=0, le=MAX_BREATHING_CYCLES)
    steps_completed: int = Field(ge=0, le=MAX_STEP_COUNT)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = None
    profile_id: str | None = None


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


def create_app(
    database_path: str | Path | None = None,
    model_reply=None,
) -> FastAPI:
    db_path = Path(database_path) if database_path is not None else default_database_path()
    initialize_database(db_path)
    reply_function = model_reply or model.generate_recommendation
    app = FastAPI(title="Still Coursework Prototype", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def db_connection():
        return managed_connection(db_path)

    def profile_or_404(connection: sqlite3.Connection, profile_id: str | None):
        if profile_id is None:
            return None
        profile = connection.execute(
            "SELECT id, display_name, preferred_exercise_id FROM profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
        if profile is None:
            raise HTTPException(status_code=404, detail="Saved profile not found.")
        return profile

    def conversation_or_create(
        connection: sqlite3.Connection,
        requested_id: str | None,
        profile_id: str | None,
    ) -> str:
        if requested_id:
            row = connection.execute(
                "SELECT id, profile_id FROM conversations WHERE id = ?", (requested_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            if row["profile_id"] != profile_id:
                raise HTTPException(
                    status_code=409,
                    detail="This conversation belongs to a different profile. Start a new chat after changing profiles.",
                )
            return requested_id
        conversation_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO conversations (id, profile_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, profile_id, now, now),
        )
        return conversation_id

    def profile_activity_context(connection: sqlite3.Connection, profile_id: str | None) -> dict[str, Any]:
        if profile_id is None:
            return {
                "preferred_exercise_id": None,
                "recent_recommendation_ids": [],
                "recently_used_exercise_ids": [],
            }
        profile = connection.execute(
            "SELECT preferred_exercise_id FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        recent_recommendations = connection.execute(
            """SELECT exercise_id FROM recommendations WHERE profile_id = ?
               ORDER BY created_at DESC LIMIT 5""",
            (profile_id,),
        ).fetchall()
        recent_sessions = connection.execute(
            """SELECT practice_id FROM exercise_sessions WHERE profile_id = ?
               ORDER BY started_at DESC LIMIT 5""",
            (profile_id,),
        ).fetchall()
        return {
            "preferred_exercise_id": profile["preferred_exercise_id"] if profile else None,
            "recent_recommendation_ids": [row["exercise_id"] for row in recent_recommendations],
            "recently_used_exercise_ids": [row["practice_id"] for row in recent_sessions],
        }

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
            "practice_version": EXERCISES[PRACTICE_ID]["script_version"],
            "planned_duration_seconds": PLANNED_DURATION_MS[BREATHING_ID] // 1000,
            "live_model_key_present": bool(key),
            "exercises": [dict(summary) for summary in EXERCISES.values()],
        }

    @app.get("/api/profiles")
    def list_profiles() -> dict[str, list[dict[str, object]]]:
        with db_connection() as connection:
            rows = connection.execute(
                """SELECT id, display_name, preferred_exercise_id, created_at, updated_at
                   FROM profiles ORDER BY updated_at DESC LIMIT 50"""
            ).fetchall()
            profiles: list[dict[str, object]] = []
            for row in rows:
                recommendations = [
                    dict(recommendation)
                    for recommendation in connection.execute(
                        """SELECT id, exercise_id, source, created_at FROM recommendations
                           WHERE profile_id = ? ORDER BY created_at DESC LIMIT 10""",
                        (row["id"],),
                    ).fetchall()
                ]
                profiles.append({**dict(row), "recommendations": recommendations})
        return {"profiles": profiles}

    @app.post("/api/profiles", status_code=201)
    def create_profile(body: ProfileCreate) -> dict[str, object]:
        display_name = body.display_name.strip()
        if not display_name:
            raise HTTPException(status_code=422, detail="Enter a short profile label.")
        now = utc_now()
        profile_id = str(uuid.uuid4())
        with db_connection() as connection:
            connection.execute(
                """INSERT INTO profiles (id, display_name, preferred_exercise_id, created_at, updated_at)
                   VALUES (?, ?, NULL, ?, ?)""",
                (profile_id, display_name, now, now),
            )
        return {
            "id": profile_id,
            "display_name": display_name,
            "preferred_exercise_id": None,
            "created_at": now,
            "updated_at": now,
            "recommendations": [],
        }

    @app.delete("/api/profiles/{profile_id}")
    def delete_profile(profile_id: str) -> dict[str, int]:
        with db_connection() as connection:
            profile = connection.execute("SELECT id FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if profile is None:
                raise HTTPException(status_code=404, detail="Saved profile not found.")
            recommendation_count = connection.execute(
                "SELECT COUNT(*) FROM recommendations WHERE profile_id = ?", (profile_id,)
            ).fetchone()[0]
            connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        return {"deleted_profiles": 1, "deleted_recommendations": recommendation_count}

    @app.post("/api/sessions", status_code=201)
    def start_session(body: SessionCreate) -> dict[str, object]:
        session_id = str(uuid.uuid4())
        now = utc_now()
        version = str(EXERCISES[body.practice_id]["script_version"])
        with db_connection() as connection:
            profile = profile_or_404(connection, body.profile_id)
            connection.execute(
                """INSERT INTO exercise_sessions
                   (id, profile_id, practice_id, script_version, status, started_at, updated_at)
                   VALUES (?, ?, ?, ?, 'in_progress', ?, ?)""",
                (session_id, body.profile_id, body.practice_id, version, now, now),
            )
            if profile is not None:
                connection.execute(
                    "UPDATE profiles SET preferred_exercise_id = ?, updated_at = ? WHERE id = ?",
                    (body.practice_id, now, body.profile_id),
                )
        return {
            "id": session_id,
            "profile_id": body.profile_id,
            "practice_id": body.practice_id,
            "script_version": version,
            "status": "in_progress",
            "started_at": now,
            "planned_duration_seconds": PLANNED_DURATION_MS[body.practice_id] // 1000,
        }

    @app.patch("/api/sessions/{session_id}")
    def update_session(session_id: str, body: SessionUpdate) -> dict[str, object]:
        now = utc_now()
        finished_at = now if body.status in {"completed", "ended_early", "interrupted"} else None
        with db_connection() as connection:
            row = connection.execute(
                "SELECT id, practice_id, status FROM exercise_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Exercise session not found.")
            if row["status"] in {"completed", "ended_early", "interrupted"}:
                raise HTTPException(status_code=409, detail="This exercise session has ended.")
            if body.status == "completed":
                exercise = EXERCISES[row["practice_id"]]
                required_duration = PLANNED_DURATION_MS[row["practice_id"]]
                progress_complete = (
                    body.cycles_completed >= int(exercise["cycle_count"])
                    if exercise["kind"] == "cycles"
                    else body.steps_completed >= len(exercise["steps"])
                )
                if body.active_duration_ms < required_duration or not progress_complete:
                    raise HTTPException(
                        status_code=422,
                        detail="The selected exercise sequence is not complete yet.",
                    )
            connection.execute(
                """UPDATE exercise_sessions SET status = ?, active_duration_ms = ?,
                   elapsed_duration_ms = ?, cycles_completed = ?, steps_completed = ?,
                   updated_at = ?, finished_at = ? WHERE id = ?""",
                (
                    body.status,
                    body.active_duration_ms,
                    body.elapsed_duration_ms,
                    body.cycles_completed,
                    body.steps_completed,
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
            "steps_completed": body.steps_completed,
            "finished_at": finished_at,
        }

    @app.get("/api/history")
    def history() -> dict[str, list[dict[str, object]]]:
        with db_connection() as connection:
            sessions = [
                dict(row)
                for row in connection.execute(
                    """SELECT s.id, s.profile_id, p.display_name AS profile_name, s.practice_id,
                              s.script_version, s.status, s.active_duration_ms,
                              s.elapsed_duration_ms, s.cycles_completed, s.steps_completed,
                              s.started_at, s.finished_at
                       FROM exercise_sessions s LEFT JOIN profiles p ON p.id = s.profile_id
                       ORDER BY s.started_at DESC LIMIT 100"""
                ).fetchall()
            ]
            conversations = [
                dict(row)
                for row in connection.execute(
                    """SELECT c.id, c.profile_id, p.display_name AS profile_name,
                              c.created_at, c.updated_at
                       FROM conversations c LEFT JOIN profiles p ON p.id = c.profile_id
                       ORDER BY c.updated_at DESC LIMIT 100"""
                ).fetchall()
            ]
            messages = [
                dict(row)
                for row in connection.execute(
                    """SELECT id, conversation_id, role, text, source, created_at
                       FROM messages ORDER BY created_at ASC LIMIT 500"""
                ).fetchall()
            ]
            recommendations = [
                dict(row)
                for row in connection.execute(
                    """SELECT r.id, r.profile_id, p.display_name AS profile_name,
                              r.conversation_id, r.exercise_id, r.source, r.created_at
                       FROM recommendations r JOIN profiles p ON p.id = r.profile_id
                       ORDER BY r.created_at DESC LIMIT 100"""
                ).fetchall()
            ]
        return {
            "sessions": sessions,
            "conversations": conversations,
            "messages": messages,
            "recommendations": recommendations,
        }

    @app.delete("/api/history")
    def clear_history() -> dict[str, int]:
        with db_connection() as connection:
            recommendation_count = connection.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
            message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            conversation_count = connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            session_count = connection.execute("SELECT COUNT(*) FROM exercise_sessions").fetchone()[0]
            profile_count = connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
            connection.execute("DELETE FROM recommendations")
            connection.execute("DELETE FROM messages")
            connection.execute("DELETE FROM conversations")
            connection.execute("DELETE FROM exercise_sessions")
            connection.execute("UPDATE profiles SET preferred_exercise_id = NULL")
        return {
            "deleted_messages": message_count,
            "deleted_conversations": conversation_count,
            "deleted_sessions": session_count,
            "deleted_recommendations": recommendation_count,
            "preserved_profiles": profile_count,
        }

    @app.post("/api/chat", status_code=201)
    async def chat(body: ChatRequest) -> dict[str, object]:
        message = body.message.strip()
        if not message:
            raise HTTPException(status_code=422, detail="Enter a short fictional example or leave this optional field blank.")

        crisis_match = contains_limited_crisis_phrase(message)
        now = utc_now()
        with db_connection() as connection:
            profile = profile_or_404(connection, body.profile_id)
            conversation_id = conversation_or_create(connection, body.conversation_id, body.profile_id)
            if crisis_match:
                # The triggering text is deliberately neither persisted nor sent to a model.
                connection.execute(
                    """INSERT INTO messages (id, conversation_id, role, text, source, created_at)
                       VALUES (?, ?, 'assistant', ?, 'fixed', ?)""",
                    (
                        str(uuid.uuid4()),
                        conversation_id,
                        "The app displayed its fixed Crisis support panel. No message text was stored.",
                        now,
                    ),
                )
                connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
                )
                return {
                    "conversation_id": conversation_id,
                    "profile_id": body.profile_id,
                    "reply": CRISIS_REPLY,
                    "source": "fixed",
                    "crisis_route": True,
                    "message_saved": False,
                    "recommendation": None,
                    "notice": "A limited phrase rule matched. This is not a distress detector.",
                }

            recent_rows = connection.execute(
                """SELECT role, text FROM messages WHERE conversation_id = ?
                   ORDER BY created_at DESC LIMIT 6""",
                (conversation_id,),
            ).fetchall()
            recent_history = [dict(row) for row in reversed(recent_rows)]
            activity_context = profile_activity_context(connection, body.profile_id)
            connection.execute(
                """INSERT INTO messages (id, conversation_id, role, text, source, created_at)
                   VALUES (?, ?, 'user', ?, 'user', ?)""",
                (str(uuid.uuid4()), conversation_id, message, now),
            )

        try:
            result = await reply_function(message, recent_history, activity_context)
        except Exception:
            result = {
                "reply": model.fallback_reply(message),
                "exercise_id": None,
                "source": "fallback",
            }
        if not isinstance(result, dict):
            result = {}
        reply = result.get("reply")
        source = result.get("source")
        exercise_id = result.get("exercise_id")
        if not isinstance(reply, str) or not reply.strip() or source not in {"gemini", "mock", "fallback"}:
            reply = model.fallback_reply(message)
            source = "fallback"
            exercise_id = None
        reply = reply.strip()[:500]
        if not isinstance(exercise_id, str) or exercise_id not in EXERCISES:
            exercise_id = None
        elif source in {"gemini", "mock", "fallback"}:
            reply = model.ensure_goal_bridge(message, recent_history, reply)
        reply_source = source
        reply_constrained = False
        if source in {"gemini", "mock"}:
            reply, reply_constrained = model.constrain_reply(message, reply)
            if reply_constrained:
                reply_source = "fixed"

        saved_at = utc_now()
        recommendation = None
        with db_connection() as connection:
            connection.execute(
                """INSERT INTO messages (id, conversation_id, role, text, source, created_at)
                   VALUES (?, ?, 'assistant', ?, ?, ?)""",
                (str(uuid.uuid4()), conversation_id, reply, reply_source, saved_at),
            )
            if exercise_id and source in {"gemini", "mock", "fallback"}:
                exercise = exercise_summary(exercise_id)
                recommendation_id = None
                recommendation_source = result.get("recommendation_source", source)
                if recommendation_source not in {"gemini", "mock", "fallback"}:
                    recommendation_source = source
                if profile is not None:
                    recommendation_id = str(uuid.uuid4())
                    connection.execute(
                        """INSERT INTO recommendations
                           (id, profile_id, conversation_id, exercise_id, source, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            recommendation_id,
                            body.profile_id,
                            conversation_id,
                            exercise_id,
                            recommendation_source,
                            saved_at,
                        ),
                    )
                    connection.execute(
                        "UPDATE profiles SET updated_at = ? WHERE id = ?",
                        (saved_at, body.profile_id),
                    )
                recommendation = {
                    **exercise,
                    "recommendation_id": recommendation_id,
                    "saved_to_profile": bool(recommendation_id),
                    "source": recommendation_source,
                }
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (saved_at, conversation_id)
            )
        return {
            "conversation_id": conversation_id,
            "profile_id": body.profile_id,
            "reply": reply,
            "source": reply_source,
            "crisis_route": False,
            "message_saved": True,
            "recommendation": recommendation,
            "notice": (
                "The app limited that reply. It can suggest only its five fixed practices and cannot start one; you choose whether to use the practice button."
                if reply_constrained
                else f"Live Gemini response from {model.model_configuration()[1]}."
                if source == "gemini"
                else "Preset demo response and rule-based suggestion; no live model was called."
                if source == "mock"
                else "Gemini could not be reached. The option below is selected by Still's local rules from its fixed practices, not by a live Gemini reply. You choose whether to use it."
                if source == "fallback" and recommendation is not None
                else "The live model could not be reached; no exercise was saved as a recommendation."
            ),
        }

    return app


app = create_app()
