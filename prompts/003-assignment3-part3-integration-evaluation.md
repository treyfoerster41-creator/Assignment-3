# Prompt record 003 — Assignment 3.3 integration and evaluation

Curated implementation summary; this is not a full conversation export.

## Student request

The student asked to move to Assignment 3 Part 3 and finish the breathing/meditation app. They specifically asked to implement a live Gemini chat and let that conversation suggest another exercise beyond the in/out breathing practice, add a separate Profile screen for creating and saving a person/profile, and save recommended exercises in that profile. They also supplied the Part 3 submission instructions requiring one `report.md` upload.

## Scope and choices

- Preserve the existing paced-breathing sequence (six cycles, four-second inhale and six-second exhale, one tap then hands-free pacing).
- Implement the second fixed course skill, 5-4-3-2-1 sensory grounding, as five automatic 15-second prompts; do not accept model-generated exercise steps.
- At the student's later request, add visual anchor, sound noticing, and support points as three short app-authored fixed options. Keep clear that these are prototype additions, not course-provided skills or study findings.
- Add local profile labels and link recommendations, selected exercise history, and fictional conversations to a profile. Do not send the profile display label to Gemini or present the local profile as an authenticated account.
- Use Gemini through backend-only HTTPX. Request a short reply and an exercise ID constrained to the five fixed skills. Validate output, persist only safe validated IDs, and use a clear preset mock when no key exists. If a live request/output fails, offer an optional locally selected fixed exercise when context permits and label it as a local fallback, never as a Gemini choice.
- Keep the exercise choice explicit and Crisis support separate from the model/backend. Use fictional content only.
- Add 15 fictional scenarios and three behavior invariants. Separate mock/software results from any live model output. The student configured a key in the ignored `.env`. After the 3.8 model repeatedly returned 503 and an initial 3.6 response was truncated at 160 tokens, set the model to 3.6 and raise the cap to 512; a direct fictional request and an end-to-end browser chat then succeeded.
- After the student reported that “hi” received a static-looking response, make the chat visibly conversational with a short transcript, greeting follow-up, and fixed-rule suggestions for fictional requests. Later, when the student asked for the assistant to guide the conversation back to a skill, instruct it to keep a stated goal across a brief side topic, put the optional suggestion beside the latest reply, and never start the skill.
- The student requested that reduced motion keep the breathing ball at one size and make spoken cues warmer and more energetic. Implement a static-size override and modestly encouraging optional wording while keeping pressure out of the prompt and acknowledging that voice quality depends on the device.
- The student then showed replies that said the bot was “starting” an exercise. Clarify that chat may suggest only a fixed app exercise, cannot invent an activity, and cannot start any exercise. Tighten the model instruction and add an API-side text guard that replaces activity advice and start claims with app-owned boundary copy. The exercise ID remains enum-validated; starting still requires the user's explicit practice-button action.

## Revised approach

The first version of the scenario API test used a test stub that returned each fixture's expected exercise ID. I changed it to invoke the real deterministic mock recommendation path so the choices were actually checked, then expanded it from 15 to 18 fictional cases to include the three app-authored practices. A run that reused one profile exposed an expected history effect: a vague prompt inherited the previous recommendation. I gave each scenario a separate synthetic profile, seeded S11 with a previously chosen grounding practice, and retained a separate test that confirms profile history can guide a vague follow-up. After the student showed replies claiming a practice had started and suggesting activities in free text, I added two API tests with mocked overreach and a server-side reply guard. The student later pointed out that a live provider fallback still left no visible exercise. I changed that path to offer a fixed local-rule option, label it as fallback, and save its source distinctly. A database migration preserves rows while expanding the exercise/source constraints. I also made the API append a short, app-authored bridge when a stated de-stress goal would otherwise disappear from a later model reply. The latest suite passes 33 tests.

## Evidence and limits

The run also includes mocked Gemini transport checks, an additive database migration check, profile/history tests, five fixed script/timing checks, guided-goal mock coverage, and invalid-output/provider-fallback checks. The 3.8 model returned HTTP 503; the first 3.6 response was cut off at the initial output-token limit. After raising the limit, Codex sent a fictional message through the in-app browser and verified a live Gemini reply plus a fixed grounding suggestion. This agent-run check created one fictional unprofiled conversation in the existing local history. The latest prompt and local fallback behavior have only been verified with mocks, not another live Gemini exchange. The student review, accessible links to recordings, final commit, and Canvas upload remain pending until they actually occur.

The current mock is a deterministic local rule set, not a conversational model and not an evaluation of Gemini's semantic behavior. The sensory-grounding sequence has no alternate prompt for a sense that does not fit a person; this remains a limitation to review and test. No user study or clinical outcome is claimed.
