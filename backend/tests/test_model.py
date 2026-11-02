from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app import model
from app.exercises import (
    BREATHING_ID,
    CONTACT_POINTS_ID,
    EXERCISE_IDS,
    GROUNDING_ID,
    SOUND_NOTICING_ID,
    VISUAL_ANCHOR_ID,
)


class GeminiTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_unavailable_gets_one_bounded_retry(self) -> None:
        attempts = 0

        def handle(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503)
            return httpx.Response(200, json={
                "candidates": [{"content": {"parts": [{"text": json.dumps({
                    "reply": "Hi! Would you rather breathe steadily or notice the room?",
                    "exercise_id": GROUNDING_ID,
                })}]}}]
            })

        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("app.model.model_configuration", return_value=("test-only-key", "gemini-3.6-flash")), \
             patch("app.model.httpx.AsyncClient", return_value=client), \
             patch("app.model.asyncio.sleep", new_callable=AsyncMock) as sleep:
            result = await model.request_gemini_recommendation("Hi!", [], {})

        self.assertEqual(attempts, 2)
        sleep.assert_awaited_once_with(1.0)
        self.assertEqual(result["exercise_id"], GROUNDING_ID)

    async def test_structured_gemini_request_uses_backend_key_and_fixed_exercise_enum(self) -> None:
        captured: dict[str, object] = {}

        def handle(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["key_header"] = request.headers.get("x-goog-api-key")
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json={
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "reply": "A brief response to this fictional example.",
                                "exercise_id": GROUNDING_ID,
                            })
                        }]
                    }
                }]
            })

        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("app.model.model_configuration", return_value=("test-only-key", "gemini-3.6-flash")), \
             patch("app.model.httpx.AsyncClient", return_value=client):
            result = await model.request_gemini_recommendation(
                "A fictional student wants to notice the room.",
                [{"role": "user", "text": "Earlier fictional turn."}],
                {
                    "preferred_exercise_id": BREATHING_ID,
                    "recent_recommendation_ids": [BREATHING_ID],
                    "recently_used_exercise_ids": [BREATHING_ID],
                },
            )

        self.assertEqual(result["exercise_id"], GROUNDING_ID)
        self.assertEqual(captured["url"], "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent")
        self.assertEqual(captured["key_header"], "test-only-key")
        payload = captured["payload"]
        self.assertEqual(payload["generationConfig"]["thinkingConfig"]["thinkingLevel"], "LOW")
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 512)
        self.assertNotIn("temperature", payload["generationConfig"])
        enum_values = payload["generationConfig"]["responseFormat"]["text"]["schema"]["properties"]["exercise_id"]["enum"]
        self.assertEqual(set(enum_values), set(EXERCISE_IDS))
        context_text = payload["contents"][-1]["parts"][0]["text"]
        self.assertIn("A fictional student wants to notice the room.", context_text)
        self.assertNotIn("display_name", context_text)
        self.assertIn("brief, warm, conversational reply", payload["system_instruction"]["parts"][0]["text"])
        self.assertIn("Never say or imply that you are starting", payload["system_instruction"]["parts"][0]["text"])
        self.assertIn("exactly five fixed practices", payload["system_instruction"]["parts"][0]["text"])

    async def test_unparseable_gemini_output_uses_fixed_local_recommendation(self) -> None:
        def handle(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("app.model.model_configuration", return_value=("test-only-key", "gemini-3.6-flash")), \
             patch("app.model.httpx.AsyncClient", return_value=client):
            result = await model.generate_recommendation(
                "A fictional student asks for a short practice.", [], {"preferred_exercise_id": None}
            )

        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["exercise_id"], BREATHING_ID)
        self.assertEqual(result["recommendation_source"], "fallback")
        self.assertIn("one short option below", result["reply"])
        self.assertNotIn("Gemini", result["reply"])

    async def test_truncated_gemini_output_uses_fixed_local_recommendation(self) -> None:
        def handle(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "candidates": [{
                    "finishReason": "MAX_TOKENS",
                    "content": {"parts": [{"text": "Here"}]},
                }]
            })

        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("app.model.model_configuration", return_value=("test-only-key", "gemini-3.6-flash")), \
             patch("app.model.httpx.AsyncClient", return_value=client):
            result = await model.generate_recommendation(
                "A fictional student asks for a short practice.", [], {"preferred_exercise_id": None}
            )

        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["exercise_id"], BREATHING_ID)
        self.assertNotIn("Gemini", result["reply"])
        self.assertIn("one short option below", result["reply"])

    async def test_model_failure_carries_pause_goal_through_side_topic_into_local_option(self) -> None:
        history = [
            {"role": "user", "text": "I want to de-stress."},
            {"role": "assistant", "text": "What has been on your mind today?"},
        ]
        with patch("app.model.model_configuration", return_value=("test-only-key", "gemini-3.6-flash")), \
             patch("app.model.request_gemini_recommendation", side_effect=RuntimeError("provider unavailable")):
            result = await model.generate_recommendation(
                "Fortnite, the new One Piece season.", history, {}
            )

        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["exercise_id"], VISUAL_ANCHOR_ID)
        self.assertIn("wanting a pause", result["reply"])
        self.assertEqual(result["recommendation_source"], "fallback")

    async def test_greeting_in_local_demo_starts_conversation_without_suggestion(self) -> None:
        with patch("app.model.model_configuration", return_value=(None, "gemini-3.6-flash")):
            result = await model.generate_recommendation(
                "Hi!", [], {"preferred_exercise_id": None}
            )

        self.assertEqual(result["source"], "mock")
        self.assertIsNone(result["exercise_id"])
        self.assertTrue(result["reply"].startswith("Hi,"))
        self.assertEqual(
            result["reply"],
            "Hi, I hear that you're looking to de-stress right now, is there anything specific you want to do?",
        )
        self.assertNotIn("Gemini", result["reply"])

    def test_request_for_something_other_than_breathing_selects_grounding_in_mock(self) -> None:
        result = model._mock_exercise(
            "Fictional example: I want a different exercise, something other than breathing.",
            {"preferred_exercise_id": BREATHING_ID},
        )
        self.assertEqual(result, GROUNDING_ID)

    def test_three_additional_fixed_options_can_be_selected_in_mock(self) -> None:
        cases = (
            ("The fictional student asks to focus on one object in view.", VISUAL_ANCHOR_ID),
            ("The demo user asks to listen to nearby sounds.", SOUND_NOTICING_ID),
            ("The fictional student wants to notice where they are supported.", CONTACT_POINTS_ID),
        )
        for message, expected_id in cases:
            with self.subTest(expected_id=expected_id):
                self.assertEqual(model._mock_exercise(message, {}), expected_id)

    def test_guided_mock_carries_pause_goal_through_game_side_topic(self) -> None:
        history = [
            {"role": "user", "text": "I want to de-stress."},
            {"role": "assistant", "text": "What has been on your mind today?"},
        ]
        self.assertEqual(model._mock_exercise("Fortnite, the new One Piece season.", {}, history), VISUAL_ANCHOR_ID)
        reply = model._mock_reply("Fortnite, the new One Piece season.", history)
        self.assertIn("since you mentioned wanting to de-stress", reply.casefold())
        self.assertIn("option below", reply.casefold())

    def test_greeting_fallback_starts_a_conversation_without_provider_diagnostics(self) -> None:
        reply = model.fallback_reply("Hi!")

        self.assertEqual(
            reply,
            "Hi, I hear that you're looking to de-stress right now, is there anything specific you want to do?",
        )
        self.assertNotIn("Gemini", reply)


if __name__ == "__main__":
    unittest.main()
