from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import httpx

from app.main import create_app


class StillApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.model_calls = []

        async def mock_model_reply(message: str, history: list[dict[str, str]]) -> tuple[str, str]:
            self.model_calls.append((message, history))
            return "A short fictional response from the mocked model.", "mock"

        self.app = create_app(self.database_path, mock_model_reply)
        self.transport = httpx.ASGITransport(app=self.app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        self.temp_dir.cleanup()

    async def test_health_and_demo_mode_are_available(self) -> None:
        self.assertEqual((await self.client.get("/api/health")).json()["status"], "ok")
        info = (await self.client.get("/api/info")).json()
        self.assertEqual(info["planned_duration_seconds"], 60)
        self.assertIn(info["model_mode"], {"mock", "live"})
        self.assertNotIn("api_key", info)

    async def test_session_history_persists_and_only_completes_at_one_minute(self) -> None:
        started = await self.client.post("/api/sessions", json={"practice_id": "breathing-4-6"})
        self.assertEqual(started.status_code, 201)
        session_id = started.json()["id"]

        early_completion = await self.client.patch(f"/api/sessions/{session_id}", json={
            "status": "completed",
            "active_duration_ms": 59_999,
            "elapsed_duration_ms": 59_999,
            "cycles_completed": 5,
        })
        self.assertEqual(early_completion.status_code, 422)

        completed = await self.client.patch(f"/api/sessions/{session_id}", json={
            "status": "completed",
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

    async def test_early_exit_is_saved_with_actual_progress(self) -> None:
        session = (await self.client.post("/api/sessions", json={})).json()
        updated = await self.client.patch(f"/api/sessions/{session['id']}", json={
            "status": "ended_early",
            "active_duration_ms": 12_400,
            "elapsed_duration_ms": 20_000,
            "cycles_completed": 1,
        })
        self.assertEqual(updated.json()["status"], "ended_early")
        self.assertEqual(updated.json()["active_duration_ms"], 12_400)

    async def test_chat_saves_user_and_mock_reply(self) -> None:
        result = await self.client.post("/api/chat", json={"message": "A fictional classroom check-in."})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["source"], "mock")
        self.assertTrue(result.json()["message_saved"])
        self.assertEqual(len(self.model_calls), 1)

        history = (await self.client.get("/api/history")).json()
        self.assertEqual(len(history["conversations"]), 1)
        self.assertEqual([row["role"] for row in history["messages"]], ["user", "assistant"])

    async def test_crisis_phrase_route_does_not_store_or_send_triggering_text(self) -> None:
        secret_fixture_text = "I am thinking about suicide in this fictional scenario."
        result = await self.client.post("/api/chat", json={"message": secret_fixture_text})
        self.assertTrue(result.json()["crisis_route"])
        self.assertFalse(result.json()["message_saved"])
        self.assertEqual(self.model_calls, [])

        history = (await self.client.get("/api/history")).json()
        self.assertNotIn(secret_fixture_text, [row["text"] for row in history["messages"]])
        self.assertEqual(len(history["messages"]), 1)
        self.assertEqual(history["messages"][0]["source"], "fixed")

    async def test_provider_failure_returns_only_sanitized_fallback(self) -> None:
        async def failing_model_reply(_message: str, _history: list[dict[str, str]]) -> tuple[str, str]:
            raise RuntimeError("private provider URL and secret details")

        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(self.database_path, failing_model_reply)),
            base_url="http://test",
        )
        response = await client.post("/api/chat", json={"message": "Fictional sample."})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["source"], "fallback")
        self.assertNotIn("private provider", response.text)
        await client.aclose()

    async def test_clear_history_deletes_conversations_messages_and_sessions(self) -> None:
        await self.client.post("/api/sessions", json={})
        await self.client.post("/api/chat", json={"message": "Fictional sample."})
        deleted = (await self.client.delete("/api/history")).json()
        self.assertEqual(deleted["deleted_sessions"], 1)
        self.assertEqual(deleted["deleted_messages"], 2)
        self.assertEqual(deleted["deleted_conversations"], 1)
        self.assertEqual((await self.client.get("/api/history")).json(), {
            "sessions": [], "conversations": [], "messages": []
        })

    async def test_crisis_event_only_records_that_fixed_panel_was_shown(self) -> None:
        await self.client.post("/api/chat", json={"message": "I cannot stay safe tonight."})
        with closing(sqlite3.connect(self.database_path)) as connection:
            text = connection.execute("SELECT text FROM messages").fetchone()[0]
        self.assertIn("No message text was stored", text)
        self.assertNotIn("tonight", text)


if __name__ == "__main__":
    unittest.main()
