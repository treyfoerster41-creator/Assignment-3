from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import httpx

from app.database import initialize_database
from app.exercises import (
    BREATHING_ID,
    CONTACT_POINTS_ID,
    EXERCISES,
    EXERCISE_IDS,
    GROUNDING_ID,
    SOUND_NOTICING_ID,
    VISUAL_ANCHOR_ID,
)
from app.main import create_app
from app import model


class StillApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.model_calls = []

        async def mock_model_reply(
            message: str,
            history: list[dict[str, str]],
            profile_context: dict[str, object],
        ) -> dict[str, object]:
            self.model_calls.append((message, history, profile_context))
            normalized = message.casefold()
            if any(term in normalized for term in ("ground", "room", "surround", "sense", "look around")):
                exercise_id = GROUNDING_ID
            elif any(term in normalized for term in ("breath", "breathe")):
                exercise_id = BREATHING_ID
            else:
                exercise_id = profile_context.get("preferred_exercise_id") or BREATHING_ID
            return {
                "reply": "A short fictional response from the mocked model.",
                "exercise_id": exercise_id,
                "source": "mock",
            }

        self.app = create_app(self.database_path, mock_model_reply)
        self.transport = httpx.ASGITransport(app=self.app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        self.temp_dir.cleanup()

    async def create_profile(self, name: str = "Jordan (fictional)") -> dict[str, object]:
        response = await self.client.post("/api/profiles", json={"display_name": name})
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_health_and_model_mode_are_available_without_exposing_key(self) -> None:
        self.assertEqual((await self.client.get("/api/health")).json()["status"], "ok")
        info = (await self.client.get("/api/info")).json()
        self.assertEqual(info["planned_duration_seconds"], 60)
        self.assertIn(info["model_mode"], {"mock", "live"})
        self.assertNotIn("api_key", info)
        self.assertEqual({item["id"] for item in info["exercises"]}, set(EXERCISE_IDS))

    async def test_breathing_session_completes_only_after_six_cycles_and_one_minute(self) -> None:
        started = await self.client.post("/api/sessions", json={"practice_id": BREATHING_ID})
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.json()["planned_duration_seconds"], 60)
        session_id = started.json()["id"]

        payload = {
            "status": "completed",
            "active_duration_ms": 59_999,
            "elapsed_duration_ms": 59_999,
            "cycles_completed": 5,
            "steps_completed": 0,
        }
        early_completion = await self.client.patch(f"/api/sessions/{session_id}", json=payload)
        self.assertEqual(early_completion.status_code, 422)

        completed = await self.client.patch(f"/api/sessions/{session_id}", json={
            **payload,
            "active_duration_ms": 60_000,
            "elapsed_duration_ms": 60_000,
            "cycles_completed": 6,
        })
        self.assertEqual(completed.json()["status"], "completed")

        restarted_app = create_app(self.database_path)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted_app), base_url="http://test"
        ) as restarted_client:
            rows = (await restarted_client.get("/api/history")).json()["sessions"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "completed")
        self.assertEqual(rows[0]["cycles_completed"], 6)

    async def test_grounding_is_a_fixed_five_prompt_seventy_five_second_sequence(self) -> None:
        started = await self.client.post("/api/sessions", json={"practice_id": GROUNDING_ID})
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.json()["planned_duration_seconds"], 75)
        session_id = started.json()["id"]

        incomplete = await self.client.patch(f"/api/sessions/{session_id}", json={
            "status": "completed",
            "active_duration_ms": 74_999,
            "elapsed_duration_ms": 74_999,
            "cycles_completed": 0,
            "steps_completed": 5,
        })
        self.assertEqual(incomplete.status_code, 422)

        completed = await self.client.patch(f"/api/sessions/{session_id}", json={
            "status": "completed",
            "active_duration_ms": 75_000,
            "elapsed_duration_ms": 75_000,
            "cycles_completed": 0,
            "steps_completed": 5,
        })
        self.assertEqual(completed.json()["status"], "completed")

    async def test_additional_fixed_practices_have_server_owned_prompts_and_completion(self) -> None:
        self.assertEqual(set(EXERCISES), set(EXERCISE_IDS))
        for exercise_id in (VISUAL_ANCHOR_ID, SOUND_NOTICING_ID, CONTACT_POINTS_ID):
            with self.subTest(exercise_id=exercise_id):
                info_item = next(item for item in (await self.client.get("/api/info")).json()["exercises"] if item["id"] == exercise_id)
                self.assertEqual(info_item["duration_seconds"], 45)
                self.assertEqual(len(info_item["steps"]), 3)
                started = await self.client.post("/api/sessions", json={"practice_id": exercise_id})
                self.assertEqual(started.status_code, 201)
                self.assertEqual(started.json()["planned_duration_seconds"], 45)
                rejected = await self.client.patch(f"/api/sessions/{started.json()['id']}", json={
                    "status": "completed",
                    "active_duration_ms": 44_999,
                    "elapsed_duration_ms": 44_999,
                    "cycles_completed": 0,
                    "steps_completed": 3,
                })
                self.assertEqual(rejected.status_code, 422)
                completed = await self.client.patch(f"/api/sessions/{started.json()['id']}", json={
                    "status": "completed",
                    "active_duration_ms": 45_000,
                    "elapsed_duration_ms": 45_000,
                    "cycles_completed": 0,
                    "steps_completed": 3,
                })
                self.assertEqual(completed.json()["status"], "completed")

    async def test_unknown_exercise_cannot_start_a_session(self) -> None:
        response = await self.client.post("/api/sessions", json={"practice_id": "invented-practice"})
        self.assertEqual(response.status_code, 422)

    async def test_early_exit_is_saved_with_actual_progress(self) -> None:
        session = (await self.client.post("/api/sessions", json={})).json()
        updated = await self.client.patch(f"/api/sessions/{session['id']}", json={
            "status": "ended_early",
            "active_duration_ms": 12_400,
            "elapsed_duration_ms": 20_000,
            "cycles_completed": 1,
            "steps_completed": 0,
        })
        self.assertEqual(updated.json()["status"], "ended_early")
        self.assertEqual(updated.json()["active_duration_ms"], 12_400)

    async def test_profile_creation_recommendation_persistence_and_profile_context(self) -> None:
        profile = await self.create_profile()
        chat = await self.client.post("/api/chat", json={
            "message": "A fictional user asks to try sensory grounding in the room.",
            "profile_id": profile["id"],
        })
        result = chat.json()
        self.assertEqual(result["recommendation"]["id"], GROUNDING_ID)
        self.assertTrue(result["recommendation"]["saved_to_profile"])
        self.assertEqual(result["recommendation"]["source"], "mock")

        # Starting a user-selected practice updates the profile's lightweight preference.
        started = await self.client.post("/api/sessions", json={
            "practice_id": GROUNDING_ID,
            "profile_id": profile["id"],
        })
        self.assertEqual(started.status_code, 201)
        follow_up = await self.client.post("/api/chat", json={
            "message": "A fictional follow-up with no specific exercise request.",
            "profile_id": profile["id"],
        })
        self.assertEqual(follow_up.json()["recommendation"]["id"], GROUNDING_ID)
        self.assertEqual(self.model_calls[-1][2]["preferred_exercise_id"], GROUNDING_ID)
        self.assertIn(GROUNDING_ID, self.model_calls[-1][2]["recently_used_exercise_ids"])
        self.assertIn(GROUNDING_ID, self.model_calls[-1][2]["recent_recommendation_ids"])

        restarted_app = create_app(self.database_path)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted_app), base_url="http://test"
        ) as restarted_client:
            saved_profile = (await restarted_client.get("/api/profiles")).json()["profiles"][0]
        self.assertEqual(saved_profile["display_name"], "Jordan (fictional)")
        self.assertEqual(saved_profile["preferred_exercise_id"], GROUNDING_ID)
        self.assertEqual(len(saved_profile["recommendations"]), 2)

    async def test_without_profile_recommendation_is_not_saved_to_any_profile(self) -> None:
        response = await self.client.post("/api/chat", json={
            "message": "A fictional student requests a short breathing practice."
        })
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["recommendation"]["saved_to_profile"])
        profiles = (await self.client.get("/api/profiles")).json()["profiles"]
        self.assertEqual(profiles, [])

    async def test_recommendation_does_not_start_exercise_until_user_chooses(self) -> None:
        profile = await self.create_profile()
        response = await self.client.post("/api/chat", json={
            "message": "A fictional student asks for sensory grounding in the room.",
            "profile_id": profile["id"],
        })
        self.assertEqual(response.json()["recommendation"]["id"], GROUNDING_ID)
        self.assertEqual((await self.client.get("/api/history")).json()["sessions"], [])

        chosen = await self.client.post("/api/sessions", json={
            "practice_id": BREATHING_ID,
            "profile_id": profile["id"],
        })
        self.assertEqual(chosen.status_code, 201)
        profiles = (await self.client.get("/api/profiles")).json()["profiles"]
        self.assertEqual(profiles[0]["preferred_exercise_id"], BREATHING_ID)

    async def test_chat_cannot_claim_to_start_a_fixed_practice(self) -> None:
        async def overreaching_model_reply(_message, _history, _profile_context):
            return {
                "reply": "Starting the 5-4-3-2-1 grounding exercise now.",
                "exercise_id": GROUNDING_ID,
                "source": "gemini",
            }

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, overreaching_model_reply)),
            base_url="http://test",
        )
        response = await client.post("/api/chat", json={
            "message": "Fictional class example: I said I wanted grounding, start it right now."
        })
        result = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["source"], "fixed")
        self.assertIn("can't start a practice from chat", result["reply"])
        self.assertEqual(result["recommendation"]["id"], GROUNDING_ID)
        self.assertEqual(result["recommendation"]["source"], "gemini")
        self.assertEqual((await client.get("/api/history")).json()["sessions"], [])
        self.assertIn("cannot start one", result["notice"])
        await client.aclose()

    async def test_chat_cannot_suggest_an_invented_practice_in_free_text(self) -> None:
        async def invented_activity_reply(_message, _history, _profile_context):
            return {
                "reply": "Try yoga instead. It will work much better.",
                "exercise_id": BREATHING_ID,
                "source": "gemini",
            }

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, invented_activity_reply)),
            base_url="http://test",
        )
        response = await client.post("/api/chat", json={
            "message": "Fictional class example: what option should the app show?"
        })
        result = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(result["source"], "fixed")
        self.assertEqual(result["reply"], model.FIXED_OPTIONS_REPLY)
        self.assertEqual(result["recommendation"]["id"], BREATHING_ID)
        self.assertNotIn("yoga", result["reply"].casefold())
        self.assertEqual((await client.get("/api/history")).json()["sessions"], [])
        await client.aclose()

    async def test_conversation_cannot_be_reused_under_another_profile(self) -> None:
        first = await self.create_profile("Jordan A (fictional)")
        second = await self.create_profile("Jordan B (fictional)")
        first_chat = await self.client.post("/api/chat", json={
            "message": "Fictional class practice request.",
            "profile_id": first["id"],
        })
        calls_before = len(self.model_calls)
        switched = await self.client.post("/api/chat", json={
            "message": "Another fictional message.",
            "profile_id": second["id"],
            "conversation_id": first_chat.json()["conversation_id"],
        })
        self.assertEqual(switched.status_code, 409)
        self.assertEqual(len(self.model_calls), calls_before)

    async def test_crisis_phrase_bypasses_model_and_does_not_store_triggering_text(self) -> None:
        fictional_trigger = "In this fictional case, the student says they are thinking about suicide."
        result = await self.client.post("/api/chat", json={"message": fictional_trigger})
        self.assertTrue(result.json()["crisis_route"])
        self.assertFalse(result.json()["message_saved"])
        self.assertIsNone(result.json()["recommendation"])
        self.assertEqual(self.model_calls, [])

        history = (await self.client.get("/api/history")).json()
        self.assertNotIn(fictional_trigger, [row["text"] for row in history["messages"]])
        self.assertEqual(len(history["messages"]), 1)
        self.assertEqual(history["messages"][0]["source"], "fixed")

    async def test_provider_failure_returns_sanitized_reply_and_no_recommendation(self) -> None:
        async def failing_model_reply(_message, _history, _profile_context):
            raise RuntimeError("private provider URL and secret details")

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, failing_model_reply)),
            base_url="http://test",
        )
        profile = (await client.post("/api/profiles", json={"display_name": "Jordan (fictional)"})).json()
        response = await client.post("/api/chat", json={
            "message": "A fictional sample for the mocked service failure.",
            "profile_id": profile["id"],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["source"], "fallback")
        self.assertIsNone(response.json()["recommendation"])
        self.assertNotIn("private provider", response.text)
        self.assertEqual((await client.get("/api/profiles")).json()["profiles"][0]["recommendations"], [])
        await client.aclose()

    async def test_gemini_failure_can_save_a_transparent_fixed_local_fallback(self) -> None:
        async def locally_selected_fallback(_message, _history, _profile_context):
            return {
                "reply": "Gemini isn't responding. This option is selected by local rules, not a live Gemini choice.",
                "exercise_id": VISUAL_ANCHOR_ID,
                "source": "fallback",
                "recommendation_source": "fallback",
            }

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, locally_selected_fallback)),
            base_url="http://test",
        )
        profile = (await client.post("/api/profiles", json={"display_name": "Jordan (fictional)"})).json()
        response = await client.post("/api/chat", json={
            "message": "A fictional student wants to de-stress.",
            "profile_id": profile["id"],
        })
        result = response.json()
        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["recommendation"]["id"], VISUAL_ANCHOR_ID)
        self.assertEqual(result["recommendation"]["source"], "fallback")
        self.assertIn("local rules", result["notice"])
        saved_profile = (await client.get("/api/profiles")).json()["profiles"][0]
        self.assertEqual(saved_profile["recommendations"][0]["source"], "fallback")
        self.assertEqual((await client.get("/api/history")).json()["sessions"], [])
        await client.aclose()

    async def test_simulated_gemini_reply_is_guided_back_to_a_practice_after_side_topic(self) -> None:
        async def simulated_gemini_reply(message, _history, _profile_context):
            side_topic = "fortnite" in message.casefold()
            return {
                "reply": "That sounds fun." if side_topic else "What has been on your mind today?",
                "exercise_id": VISUAL_ANCHOR_ID if side_topic else BREATHING_ID,
                "source": "gemini",
            }

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, simulated_gemini_reply)),
            base_url="http://test",
        )
        first = await client.post("/api/chat", json={"message": "I want to de-stress."})
        second = await client.post("/api/chat", json={
            "message": "Fortnite, the new One Piece season.",
            "conversation_id": first.json()["conversation_id"],
        })
        result = second.json()
        self.assertEqual(result["source"], "gemini")
        self.assertIn("That sounds fun.", result["reply"])
        self.assertIn("Since you mentioned wanting a pause", result["reply"])
        self.assertEqual(result["recommendation"]["id"], VISUAL_ANCHOR_ID)
        self.assertEqual((await client.get("/api/history")).json()["sessions"], [])
        await client.aclose()

    async def test_invalid_model_exercise_id_is_not_saved_or_started(self) -> None:
        async def invalid_model_reply(_message, _history, _profile_context):
            return {"reply": "A bounded mock reply.", "exercise_id": "invented-skill", "source": "gemini"}

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, invalid_model_reply)),
            base_url="http://test",
        )
        profile = (await client.post("/api/profiles", json={"display_name": "Jordan (fictional)"})).json()
        response = await client.post("/api/chat", json={
            "message": "Fictional test for an invalid generated exercise ID.",
            "profile_id": profile["id"],
        })
        self.assertIsNone(response.json()["recommendation"])
        self.assertEqual((await client.get("/api/history")).json()["sessions"], [])
        self.assertEqual((await client.get("/api/profiles")).json()["profiles"][0]["recommendations"], [])
        await client.aclose()

    async def test_clear_history_deletes_recommendations_but_preserves_profiles(self) -> None:
        profile = await self.create_profile()
        await self.client.post("/api/sessions", json={"practice_id": BREATHING_ID, "profile_id": profile["id"]})
        await self.client.post("/api/chat", json={
            "message": "A fictional sample asks for paced breathing.",
            "profile_id": profile["id"],
        })
        deleted = (await self.client.delete("/api/history")).json()
        self.assertEqual(deleted["deleted_sessions"], 1)
        self.assertEqual(deleted["deleted_messages"], 2)
        self.assertEqual(deleted["deleted_conversations"], 1)
        self.assertEqual(deleted["deleted_recommendations"], 1)
        self.assertEqual(deleted["preserved_profiles"], 1)
        self.assertEqual((await self.client.get("/api/profiles")).json()["profiles"][0]["preferred_exercise_id"], None)
        history = (await self.client.get("/api/history")).json()
        self.assertEqual(history["sessions"], [])
        self.assertEqual(history["conversations"], [])
        self.assertEqual(history["messages"], [])
        self.assertEqual(history["recommendations"], [])

    async def test_deleting_profile_removes_recommendations_and_unlabels_history(self) -> None:
        profile = await self.create_profile()
        await self.client.post("/api/chat", json={
            "message": "A fictional request for the surroundings exercise.",
            "profile_id": profile["id"],
        })
        await self.client.post("/api/sessions", json={"practice_id": GROUNDING_ID, "profile_id": profile["id"]})
        deleted = await self.client.delete(f"/api/profiles/{profile['id']}")
        self.assertEqual(deleted.json()["deleted_recommendations"], 1)
        history = (await self.client.get("/api/history")).json()
        self.assertIsNone(history["sessions"][0]["profile_id"])
        self.assertIsNone(history["conversations"][0]["profile_id"])
        self.assertEqual(history["recommendations"], [])

    async def test_crisis_event_only_records_that_fixed_panel_was_shown(self) -> None:
        await self.client.post("/api/chat", json={"message": "Fictional sentence: I cannot stay safe tonight."})
        with closing(sqlite3.connect(self.database_path)) as connection:
            text = connection.execute("SELECT text FROM messages").fetchone()[0]
        self.assertIn("No message text was stored", text)
        self.assertNotIn("tonight", text)


class Assignment3Part3ScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def test_eighteen_fictional_scenarios_with_deterministic_mock_outputs(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "assignment3_part3_scenarios.json"
        scenarios = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(len(scenarios), 18)
        temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(temp_dir.name) / "scenarios.sqlite3"
        app = create_app(database_path, model.generate_recommendation)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            observed = []
            with patch("app.model.model_configuration", return_value=(None, "gemini-3.8-flash")):
                for case in scenarios:
                    profile = (await client.post("/api/profiles", json={
                        "display_name": f"Jordan {case['id']} (fictional)"
                    })).json()
                    if case["id"] == "S11":
                        await client.post("/api/sessions", json={
                            "practice_id": GROUNDING_ID,
                            "profile_id": profile["id"],
                        })
                    response = await client.post("/api/chat", json={
                        "message": case["message"],
                        "profile_id": profile["id"],
                    })
                    self.assertEqual(response.status_code, 201, case["id"])
                    result = response.json()
                    self.assertEqual(result["source"], "mock", case["id"])
                    self.assertEqual(result["recommendation"]["id"], case["expected_exercise_id"], case["id"])
                    self.assertTrue(result["recommendation"]["saved_to_profile"], case["id"])
                    self.assertIn("preset demo response", result["reply"], case["id"])
                    observed.append(case["id"])
                history = (await client.get("/api/history")).json()
                self.assertEqual(len(history["recommendations"]), 18)
                self.assertEqual(len(history["conversations"]), 18)
                recent_context = model._mock_exercise(
                    "A vague fictional follow-up.",
                    {"preferred_exercise_id": None, "recent_recommendation_ids": [GROUNDING_ID]},
                )
                self.assertEqual(recent_context, GROUNDING_ID)
            self.assertEqual(observed, [case["id"] for case in scenarios])
        temp_dir.cleanup()


class ExistingDatabaseMigrationTests(unittest.TestCase):
    def test_old_part2_database_migrates_without_deleting_existing_rows(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(temp_dir.name) / "old.sqlite3"
        with closing(sqlite3.connect(database_path)) as connection:
            connection.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE conversations (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE exercise_sessions (
                    id TEXT PRIMARY KEY,
                    practice_id TEXT NOT NULL,
                    script_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active_duration_ms INTEGER NOT NULL DEFAULT 0,
                    elapsed_duration_ms INTEGER NOT NULL DEFAULT 0,
                    cycles_completed INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finished_at TEXT
                );
                INSERT INTO exercise_sessions
                (id, practice_id, script_version, status, active_duration_ms, elapsed_duration_ms, cycles_completed, started_at, updated_at)
                VALUES ('old-session', 'breathing-4-6', '1.0', 'completed', 60000, 60000, 6, '2026-10-21T00:00:00+00:00', '2026-10-21T00:01:00+00:00');
            """)
            connection.commit()

        initialize_database(database_path)
        with closing(sqlite3.connect(database_path)) as connection:
            row = connection.execute("SELECT id, practice_id, status, cycles_completed, steps_completed, profile_id FROM exercise_sessions").fetchone()
            self.assertEqual(row, ("old-session", "breathing-4-6", "completed", 6, 0, None))
            profile_columns = {item[1] for item in connection.execute("PRAGMA table_info(profiles)")}
            self.assertIn("preferred_exercise_id", profile_columns)
        temp_dir.cleanup()

    def test_two_option_catalog_migration_preserves_rows_and_accepts_three_new_ids(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(temp_dir.name) / "part3-two-options.sqlite3"
        with closing(sqlite3.connect(database_path)) as connection:
            connection.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE profiles (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    preferred_exercise_id TEXT CHECK (preferred_exercise_id IS NULL OR preferred_exercise_id IN ('breathing-4-6', 'grounding-54321')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE conversations (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE exercise_sessions (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
                    practice_id TEXT NOT NULL CHECK (practice_id IN ('breathing-4-6', 'grounding-54321')),
                    script_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active_duration_ms INTEGER NOT NULL DEFAULT 0,
                    elapsed_duration_ms INTEGER NOT NULL DEFAULT 0,
                    cycles_completed INTEGER NOT NULL DEFAULT 0,
                    steps_completed INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE recommendations (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
                    exercise_id TEXT NOT NULL CHECK (exercise_id IN ('breathing-4-6', 'grounding-54321')),
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                INSERT INTO profiles VALUES ('profile-1', 'Jordan (fictional)', 'breathing-4-6', 'created', 'updated');
                INSERT INTO conversations VALUES ('conversation-1', 'profile-1', 'created', 'updated');
                INSERT INTO messages VALUES ('message-1', 'conversation-1', 'user', 'Fictional demo message', 'user', 'created');
                INSERT INTO exercise_sessions VALUES ('session-1', 'profile-1', 'breathing-4-6', '1.0', 'completed', 60000, 60000, 6, 0, 'created', 'updated', 'finished');
                INSERT INTO recommendations VALUES ('recommendation-1', 'profile-1', 'conversation-1', 'grounding-54321', 'mock', 'created');
            """)
            connection.commit()

        initialize_database(database_path)
        with closing(sqlite3.connect(database_path)) as connection:
            self.assertEqual(connection.execute("SELECT id, preferred_exercise_id FROM profiles").fetchall(), [("profile-1", BREATHING_ID)])
            self.assertEqual(connection.execute("SELECT id, practice_id, status, cycles_completed FROM exercise_sessions").fetchall(), [("session-1", BREATHING_ID, "completed", 6)])
            self.assertEqual(connection.execute("SELECT id, exercise_id FROM recommendations").fetchall(), [("recommendation-1", GROUNDING_ID)])
            self.assertEqual(connection.execute("SELECT id, text FROM messages").fetchall(), [("message-1", "Fictional demo message")])
            connection.execute("UPDATE profiles SET preferred_exercise_id = ? WHERE id = ?", (VISUAL_ANCHOR_ID, "profile-1"))
            connection.execute("""INSERT INTO exercise_sessions
                (id, profile_id, practice_id, script_version, status, started_at, updated_at)
                VALUES ('session-2', 'profile-1', ?, '1.0', 'in_progress', 'now', 'now')""", (CONTACT_POINTS_ID,))
            connection.execute("""INSERT INTO recommendations
                (id, profile_id, conversation_id, exercise_id, source, created_at)
                VALUES ('recommendation-2', 'profile-1', 'conversation-1', ?, 'mock', 'now')""", (SOUND_NOTICING_ID,))
            connection.execute("""INSERT INTO recommendations
                (id, profile_id, conversation_id, exercise_id, source, created_at)
                VALUES ('recommendation-3', 'profile-1', 'conversation-1', ?, 'fallback', 'now')""", (VISUAL_ANCHOR_ID,))
            connection.commit()
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(connection.execute("SELECT preferred_exercise_id FROM profiles WHERE id = 'profile-1'").fetchone(), (VISUAL_ANCHOR_ID,))
            self.assertEqual(connection.execute("SELECT count(*) FROM exercise_sessions").fetchone(), (2,))
            self.assertEqual(connection.execute("SELECT count(*) FROM recommendations").fetchone(), (3,))
        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
