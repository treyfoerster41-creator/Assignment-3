# Assignment 3 project instructions

## Current checkpoint

- The user has started Assignment 3.2. Build a coherent working localhost prototype around the fixed 4-in/6-out breathing practice, optional conversational reflection, SQLite history, and independent Crisis support panel.
- Part 1 remains a research/design checkpoint. Its original report is archived at `docs/assignment-3-part-1-report-archive.md`; root `report.md` is for Part 2.
- Keep `report.md`, `README.md`, the design note, prompts, evidence log, AI-use disclosure, and handoff accurate to observed behavior.
- Do not commit, push, or claim Canvas submission until the student has reviewed the final Part 2 files and any manual browser/database observations that are attributed to them.

## Product boundaries

- This is a local coursework skills prototype evaluated only with fictional scenarios. Never offer, deploy, link, or recommend it to a real person as mental health support.
- Do not claim diagnosis, therapy, monitoring, or clinical effectiveness. Do not imply a person is watching messages.
- Keep selected course skill steps exact. The implemented practice is six cycles of a four-second inhale and six-second exhale. Do not let a language model invent therapeutic steps or control exercise timing, navigation, persistence, or crisis access.
- A clearly named crisis-support route must remain available on every screen and work when the model, backend, or any text-matching rule fails.
- Describe any crisis phrase matching as limited routing, not a distress detector. Never infer distress from sentiment, typing speed, pauses, or a diagnosis.
- Test with fictional scenarios only. Do not collect real identities or real distress narratives. Keep API keys and `.env` contents out of Git and evidence.

## Design decisions to preserve

- Part 1 proposed two fixed skills. Part 2 implements the breathing practice first; grounding remains a documented design option and is not claimed as implemented.
- The implemented breathing sequence is 60 seconds: six four-second inhales and six six-second exhales. Measure from the first breathing instruction through the sixth exhale; report entry/setup separately. User-chosen pauses are excluded. Never force completion or exit.
- Let the user start, pause, resume, or end the fixed sequence. Show one breathing cue at a time.
- Minimize screen interaction: one explicit start action begins the automatically advancing 60-second sequence, with no required taps while the user breathes. Keep pause, end, and Crisis support available. If voice cues are added, check them in the target browser and retain a usable visual alternative.
- Keep writing, emotional disclosure, and configuration optional. Prior use may suggest an option, but must not silently route the user or hide alternatives.
- Keep interface language neutral and low stimulus. Respect reduced-motion settings and provide a static pacing alternative.
- Gemini is accessed only through FastAPI with HTTPX. The documented model ID is `gemini-3.8-flash` (checked against Google's official API documentation on October 21, 2026). No key is configured in this project; mock mode is clearly labeled until the student configures a backend-only key in the ignored root `.env`.

## Planned architecture

- Vue owns rendering, explicit view state, timing cues, accessible controls, and loading/error display.
- FastAPI owns validation, fixed skill definitions, bounded backend-only model requests, SQLite reads/writes, and sanitized errors.
- SQLite stores only fictional local preferences, conversations, messages, exercise status/progress, and optional feedback. Provide a way to review and delete saved history.
- Model context must be relevant and bounded. The model does not execute SQL, determine crisis routing, create exercise steps, or write application records. The backend owns persistence.

## Verification and evidence

- Keep automated checks separate from manual browser/database observations and live-model responses.
- Record expected and observed results, date, browser, whether a response is mocked or live, and any limitations.
- Use mocked model responses for routine checks. If live calls are used, cap them at 50 per session and return to mocks at the limit.
- Do not claim a browser check, student VS Code review, commit, push, or Canvas submission until it actually happens.
- Include at least one failed or revised approach in the curated, redacted evidence log. Do not export the full conversation.

## Technology and project structure

- Use Vue, FastAPI, and SQLite on localhost. Current project-local versions are recorded by `frontend/package-lock.json` and `backend/requirements.txt`; the user approved the latest releases for this implementation.
- Ask before adding any future dependency beyond the approved Vue/Vite/FastAPI/Uvicorn/HTTPX stack.
- Keep credentials backend-only in an ignored local `.env`. `.env.example` contains names only, never real credentials.
- Keep the project self-contained. Do not import the Expedia Lite database, hotel data, bookings, or Geoapify code into this project.
- Clearly distinguish automated/mock checks from manual browser/database observations and live Gemini behavior. Do not call a mock response a live model result.
