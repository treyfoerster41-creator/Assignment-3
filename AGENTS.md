# Assignment 3 project instructions

## Current checkpoint

- Work on Assignment 3.1 only until the user requests the next milestone.
- Part 1 is a research and design checkpoint. The Vue, FastAPI, and SQLite application is planned, not implemented.
- Keep `report.md`, the design note, research sources, evidence log, and handoff accurate to the current state.
- Do not create a GitHub repository, push, or claim a submitted commit until the user has reviewed the final Part 1 files and the remote is known.

## Product boundaries

- This is a local coursework skills prototype evaluated only with fictional scenarios. Never offer, deploy, link, or recommend it to a real person as mental health support.
- Do not claim diagnosis, therapy, monitoring, or clinical effectiveness. Do not imply a person is watching messages.
- Keep selected course skill steps exact. Do not let a language model invent therapeutic steps or control exercise timing, navigation, persistence, or crisis access.
- A clearly named crisis-support route must remain available on every screen and work when the model, backend, or any text-matching rule fails.
- Describe any crisis phrase matching as limited routing, not a distress detector. Never infer distress from sentiment, typing speed, pauses, or a diagnosis.
- Test with fictional scenarios only. Do not collect real identities or real distress narratives. Keep API keys and `.env` contents out of Git and evidence.

## Design decisions to preserve

- The current proposal is a general meditation experience with two fixed course practices: 4-in/6-out paced breathing and 5-4-3-2-1 sensory grounding.
- Each complete planned practice is at most 90 seconds at its intended pace. Measure from first exercise instruction through final planned step; report entry/setup separately. Pauses and time viewing crisis information are excluded. Never force completion or exit.
- Offer a small user choice before an exercise, then show one skill/action at a time. Keep the user able to pause, stop, change direction, or skip a sense.
- Keep writing, emotional disclosure, and configuration optional. Prior use may suggest an option, but must not silently route the user or hide alternatives.
- Keep interface language neutral and low stimulus. Respect reduced-motion settings and provide a static pacing alternative.
- Proposed provider is Gemini through FastAPI; no key or model ID is configured in this project yet. Confirm availability and document the exact model before implementation.

## Planned architecture

- Vue owns rendering, explicit view state, timing cues, accessible controls, and loading/error display.
- FastAPI owns validation, fixed skill definitions, bounded backend-only model requests, SQLite reads/writes, and sanitized errors.
- SQLite stores only fictional local preferences, conversations, messages, exercise status/progress, and optional feedback. Provide a way to review and delete saved history.
- Model context must be relevant and bounded. The model does not execute SQL or write application records.

## Verification and evidence

- Keep automated checks separate from manual browser/database observations and live-model responses.
- Record expected and observed results, date, browser, whether a response is mocked or live, and any limitations.
- Use mocked model responses for routine checks. If live calls are used, cap them at 50 per session and return to mocks at the limit.
- Do not claim a browser check, student VS Code review, commit, push, or Canvas submission until it actually happens.
- Include at least one failed or revised approach in the curated, redacted evidence log. Do not export the full conversation.

## Technology and project structure

- Use the course's Vue, FastAPI, and SQLite stack on localhost when implementation begins.
- Keep credentials backend-only in an ignored local `.env`. `.env.example` contains names only, never real credentials.
- Keep the project self-contained. Do not import the Expedia Lite database, hotel data, bookings, or Geoapify code into this project.
- Mark planned placeholders as planned. Add setup/run commands only after a working application exists and has been checked.
