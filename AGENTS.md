# Assignment 3 project instructions

## Current checkpoint — Assignment 3.3

- Continue the Still breathing/meditation coursework prototype. Part 1 is archived at `docs/assignment-3-part-1-report-archive.md`; Part 2 is archived at `docs/assignment-3-part-2-report-archive.md`; root `report.md` is for Part 3.
- Part 3 refines the app, tests it with at least 15 fictional scenarios and behavior invariants, evaluates an appropriate limited live-model sample when credentials permit, records one surprising result and one untested limitation, and includes the required demo/process recordings and evidence.
- Keep `report.md`, README, design, prompts, evidence, AI-use disclosure, and handoff accurate to what was actually built and observed.
- Do not claim student VS Code review, student browser acceptance, a live response, a screen recording, commit, push, or Canvas upload until each actually occurs. Ask before committing or pushing if the user has not explicitly requested those actions for this milestone.

## Product boundaries

- This is a local coursework skills prototype evaluated only with fictional scenarios. Never offer, deploy, or recommend it as real mental-health support.
- Do not claim diagnosis, therapy, monitoring, or clinical effectiveness. Do not imply anyone is watching messages. Do not infer distress from clicking, sentiment, typing speed, pauses, or a diagnosis.
- Keep the two course-provided exercise scripts unchanged: paced breathing (six 4-second inhales and 6-second exhales, 60 seconds total) and 5-4-3-2-1 sensory grounding (five fixed 15-second prompts, 75 seconds total). The student later requested three optional app-authored additions: visual anchor, sound noticing, and support points (three fixed 15-second prompts each). Label these as app-authored options, not course-provided skills or study findings. Do not let a model invent steps, timing, or scripts.
- The user explicitly chooses whether to start a recommendation. The model cannot change navigation, start/pause/stop a session, write to SQLite, or control crisis routing.
- Keep a clearly named Crisis support route visible and usable on every screen. It must work when the model, backend, or any text-matching rule fails.
- Describe phrase matching as limited routing, never as a distress detector. It may miss or overmatch wording. Matched user text is not saved or sent to Gemini.
- Use fictional scenarios only. Do not enter or retain real identities, personal health details, or real distress narratives. Keep keys and `.env` contents out of Git and evidence.

## Interaction and access

- Minimize interaction during meditation. One start action begins the practice; prompts advance automatically. Keep Pause, End, and Crisis support available.
- Optional browser speech synthesis is off by default, uses no microphone, and never replaces visible cues. Keep a static/reduced-motion option.
- Keep writing, emotional disclosure, and configuration optional. Saved profile/history can influence a suggestion, but never hide alternatives or silently start an exercise.
- Keep language neutral, low stimulus, and nonjudgmental. Do not present profiles as authenticated accounts or secure cloud storage; they are local labels.

## Architecture and data

- Vue owns rendering, explicit view state, activity timing, accessible controls, and API error display. It loads exercise definitions and timing from the backend catalog, with bundled static definitions only as an offline display fallback.
- FastAPI owns validation, fixed skill definitions, bounded backend-only Gemini requests, SQLite reads/writes, and sanitized errors.
- Gemini may return a short conversational acknowledgment and one whitelisted fixed exercise ID. The server maps that ID to a fixed script. Prompt the chat to retain a stated pause/de-stress goal through a side topic and gently point to the optional suggestion. If Gemini fails, local rules may offer one fixed recommendation, clearly labeled as a local fallback rather than a live model selection. Model text is untrusted: replace text that names/suggests activities or implies a practice is starting. The model cannot invent exercises or start/pause/stop a session; only a user-selected app button can start one.
- SQLite stores local profile labels, user-selected practice preference, fictional messages, fixed exercise sessions/progress, and recommendations. Provide controls to inspect/delete history and delete a profile; deleting a profile must not silently delete the person's linked session/conversation history, though it removes recommendations.
- Keep the API key in the ignored root `.env`, backend-only. Never use `VITE_` credentials, print or log key values, log provider URLs, expose raw provider errors, or put credentials in evidence.
- Preserve existing SQLite records and deletions. Apply additive migrations. Never clear/reseed the user's database to make evidence cleaner. Automated tests must use temporary databases.
- Do not add dependencies without student approval. Part 3 uses the approved Vue/Vite/FastAPI/Uvicorn/HTTPX stack.

## Verification and evidence

- Keep automated/mock checks separate from manual browser observations and live Gemini outputs. Record expected and observed behavior, date, environment, and limitations.
- Use at least 15 distinct fictional prompts/scenarios and three explicit behavior invariants. Do not call predetermined fixtures live-model evidence.
- When a Gemini key is available, cap live calls at 50 per session and return to mocks at the limit. Without a key, document the live check as blocked/pending; never invent a model response.
- Include a failure or revised approach in the curated, redacted evidence log. Do not export the full conversation.
- The student must create/verify required demo and process screencasts. Keep `.env`, real data, and secrets out of recordings.
- Run backend tests and the frontend production build after changes. Report exact counts/results, and preserve limitations. Keep the 18 scenario fixtures identified as fictional software checks, separate from live Gemini evaluation.

## Git and submission

- Work in the existing project unless the student requests another branch/worktree. Preserve the Part 1 and Part 2 report checkpoints.
- The final Part 3 `report.md` must use first-person prose and include repository URL, exact submitted commit, links to accessible design/evidence/recordings, evaluation results, one surprising finding, one untested limitation, and the app's limits.
- Do not invent a submitted commit or accessible video URL. Leave placeholders/pending items explicit until supplied or confirmed.
- Keep all coursework software local. Do not import data or code from Expedia Lite or unrelated projects.
