# Assignment 3.3 fictional scenario checks

Run date: November 2, 2026. These checks use the deterministic local mock, temporary SQLite databases, and fictional messages only. They are not live Gemini output or participant data.

## Eighteen messages

The backend test sends each message through the actual mock selection and chat persistence path. Each case uses a separate fictional profile so earlier recommendations do not affect its expected result. S11 first records a user-selected grounding practice to confirm an explicit breathing request can override a saved preference. The exact messages and expected IDs are in [`backend/tests/fixtures/assignment3_part3_scenarios.json`](../backend/tests/fixtures/assignment3_part3_scenarios.json).

| ID | Fictional input (short description) | Expected | Observed in mock/API test |
| --- | --- | --- | --- |
| S01 | Four-in/six-out before class presentation | Paced breathing | Paced breathing; saved to the selected profile |
| S02 | Look around and name things in the room | Sensory grounding | Sensory grounding; saved to the selected profile |
| S03 | Five sights, four contact points, nearby sounds | Sensory grounding | Sensory grounding; saved to the selected profile |
| S04 | Explicit request for the fixed 4-in/6-out card | Paced breathing | Paced breathing; saved to the selected profile |
| S05 | Use classroom surroundings rather than breath counting | Sensory grounding | Sensory grounding; saved to the selected profile |
| S06 | Quiet one-minute option before a timed quiz | Paced breathing | Paced breathing; saved to the selected profile |
| S07 | Orient to a noisy room | Sensory grounding | Sensory grounding; saved to the selected profile |
| S08 | 5-4-3-2-1 with no typing | Sensory grounding | Sensory grounding; saved to the selected profile |
| S09 | Use paced breathing again | Paced breathing | Paced breathing; saved to the selected profile |
| S10 | Try the other fixed practice instead of usual breathing | Sensory grounding | Sensory grounding; saved to the selected profile |
| S11 | Saved preference is grounding; explicitly asks for breathing | Paced breathing | Paced breathing; saved to the selected profile |
| S12 | Short, low-effort option in a library | Paced breathing | Paced breathing; saved to the selected profile |
| S13 | Show grounding's sense prompts one at a time | Sensory grounding | Sensory grounding; saved to the selected profile |
| S14 | No preference; asks for a brief suggestion | Paced breathing | Paced breathing; saved to the selected profile |
| S15 | Notice things that can be seen, felt, heard, smelled, and tasted | Sensory grounding | Sensory grounding; saved to the selected profile |
| S16 | Focus on one object in view | Visual anchor | Visual anchor; saved to the selected profile |
| S17 | Notice nearby sounds | Sound noticing | Sound noticing; saved to the selected profile |
| S18 | Notice support from a chair | Support points | Support points; saved to the selected profile |

The deterministic mock is intentionally not described as natural-language Gemini. The test proves local rule selection and profile persistence for these fixtures only. It does not prove that Gemini will interpret them the same way.

## Three behavior invariants

| Invariant | Expected | Observed | Evidence |
| --- | --- | --- | --- |
| The model cannot create or start a skill | An ID outside the five fixed options is discarded; a suggested skill starts only after an explicit practice-start request. | An invented ID produced no recommendation or session. A valid suggestion created no session until a separate start call. | `test_invalid_model_exercise_id_is_not_saved_or_started`; `test_recommendation_does_not_start_exercise_until_user_chooses` |
| Crisis phrase routing bypasses model and does not retain the triggering text | A matched fictional message does not reach the model or get stored; only a fixed event is retained. | The mock call list remained empty, the response flagged `message_saved: false`, and history omitted the input text. | `test_crisis_phrase_bypasses_model_and_does_not_store_triggering_text`; `test_crisis_event_only_records_that_fixed_panel_was_shown` |
| The exercise scripts and completion conditions remain server-owned | Only the five known practice IDs are available; completion requires the fixed duration and all steps/cycles. | The health/info endpoint listed all five IDs; early completion checks were rejected and valid full completion succeeded for the fixed breathing/grounding scripts. | `test_health_and_model_mode_are_available_without_exposing_key`; `test_breathing_session_completes_only_after_six_cycles_and_one_minute`; `test_grounding_is_a_fixed_five_prompt_seventy_five_second_sequence`; `test_additional_fixed_practices_have_server_owned_prompts_and_completion` |

## Additional checks and limits

- Backend unittest run at the earlier checkpoint passed 18 tests, including the 15-case scenario loop, profile history/persistence, additive migration, fixed-output validation, and crisis routing. The current run and expanded evidence are recorded in `evidence-log.md`. The Gemini request test uses `httpx.MockTransport` and a synthetic test-only key; it verifies the endpoint shape, header placement, and five-ID schema without contacting Google.
- Frontend production build and whitespace check are recorded separately in `evidence-log.md`.
- A read-only local browser load on November 2 showed Practice/Profile/History navigation, both fixed choices, the mock-mode status, and persistent Crisis support controls. I did not submit the form or create/alter rows in the existing demo database during that browser inspection.
- A prior fictional Gemini response was observed, but the updated goal-bridging prompt and local fallback option have not been checked with a fresh live request. Mock results do not establish model quality, quota, or current provider availability.
- No participant/user test, formal screen-reader test, cross-browser check, or student acceptance is claimed. In particular, sensory prompts for smell/taste may not suit every person; no alternative prompt is currently offered.
