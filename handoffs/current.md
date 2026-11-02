# Current handoff — Assignment 3.3

Updated November 2, 2026.

## Current state

- Part 1's research/design report remains at `docs/assignment-3-part-1-report-archive.md`. Part 2's accepted checkpoint is preserved in Git history. This working tree contains uncommitted Part 3 changes on `main`.
- Part 3 includes the original two course skills plus three app-authored options (visual anchor, sound noticing, support points), a profile page, a structured Gemini REST adapter, local demo/fallback states, and migrations that preserve earlier SQLite rows.
- The chat displays the recent conversation and is prompted to carry a stated de-stress goal through a side topic, then point to the suggestion card placed just below the latest reply. The user may try the recommendation, select another practice, or skip it.
- Chat suggestions remain limited to the five fixed scripts. Server-side checks replace free text that recommends outside activities or claims that a practice has started. A user-selected practice button alone starts a session. If Gemini fails, local rules can pick a fixed option and the interface labels it as fallback, not a Gemini answer. These latest changes have mock coverage, not a fresh live-model check.
- Reduced motion now holds the breathing ball at a single size. Optional synthesized breathing cues use slightly warmer, encouraging phrasing; their voice quality depends on the browser/device and has not been confirmed audible by the student.
- Paced breathing remains one tap followed by automatic 4-second inhale/6-second exhale cues. Grounding keeps its five 15-second course prompts. Three app-authored options each have three fixed prompts at 15 seconds. Every practice can be paused or ended; spoken prompts are optional, visual cues remain, and no microphone is used.
- Profiles retain a fictional display label, last practice explicitly selected, recommendations, and linked practice/conversation history. The display label is not sent to Gemini. Profile and history controls are local, not accounts.
- The student added the Gemini key to the ignored root `.env`; the key value was not displayed. Gemini 3.8 returned HTTP 503. The ignored model setting and backend default are now `gemini-3.6-flash`; after raising the output cap from 160 to 512 and guarding against truncation, a fictional direct request returned a complete fixed-ID response. A fictional in-app browser chat then returned a live reply and the fixed grounding recommendation. No profile was selected, so the suggestion was not saved to a profile; the app's local conversation history now includes that fictional test exchange.
- The latest backend suite passes 33 unittest cases, including eighteen fictional inputs through the deterministic mock recommendation path, the five scripts, goal carryover after a side topic, provider fallback, a migration preserving prior data, and the model boundaries. The latest frontend production build and `git diff --check` pass. The earlier live check confirmed one Gemini reply and grounding recommendation before the latest prompt/fallback changes; it used no selected profile and created one fictional conversation only. The real user profile was not selected or changed.
- Frontend and backend development servers are listening locally at `http://127.0.0.1:5173/` and `http://127.0.0.1:8000/`. The browser tab is not currently open; use the frontend URL to review.
- `report.md` is an honest first-person draft. It is not ready to upload: the exact Part 3 commit, student acceptance, a fresh live check, and required recordings/links have not been supplied or recorded.

## What remains

- Student: review the current app changes in VS Code and try a fictional conversation such as “I want to de-stress” followed by a side topic like a game. Check that a suggestion appears under the reply and remains optional. If Gemini is unavailable, confirm the card is labeled local fallback.
- Student: check the five options, profile creation/selection, profile persistence, one grounding/add-on flow, reduced motion, optional speech, stop/pause, and Crisis support in the browser. Keep the key in the ignored root `.env`; do not paste it into chat.
- Student: record the required demo and process screencast, including a failure/revision, supporting evidence, and an explanation of generated/AI-assisted code. Keep the recording fictional and avoid exposing `.env` or keys.
- After review and evidence arrive, update the report with observed live results, working video links, and the exact commit; then commit/push only when the student explicitly requests it. Do not claim a Canvas upload until the student does it.

## Boundaries

Use fictional examples only. Still is a local coursework skills prototype, not mental health care. It makes no diagnosis, therapy, monitoring, or effectiveness claim. Gemini can produce a brief response and choose one fixed exercise ID; local rules can select a fixed fallback. Neither can create instructions, start an exercise, access Crisis logic, or modify the database directly. Crisis support is bundled in the interface and does not depend on the backend or model.
