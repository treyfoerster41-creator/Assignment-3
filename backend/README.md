# Still backend

FastAPI owns request validation, the fixed exercise catalog, SQLite persistence, bounded Gemini requests, and safe fallback behavior. Run it from this directory with the project-local environment active:

```sh
source .venv/bin/activate
uvicorn app.main:app --reload
```

The local database is `data/still.db`. Initialization applies additive migrations for Part 3 profiles, linked history, and recommendations. Existing conversation and session rows are preserved. Tests use temporary databases and mock the model transport; they never require a real key.

To enable Gemini, place `GEMINI_API_KEY` in the ignored project-root `.env`. The key is loaded by the backend only. The app defaults to `gemini-3.6-flash`, uses HTTPX with a finite timeout, and accepts only a completed structured reply plus one of five fixed exercise IDs. The first two scripts are course skills; visual anchor, sound noticing, and support points are app-authored additions. A 512-token output cap leaves room for Gemini's thinking tokens. If a request fails or output is invalid, the backend can use local rules to offer one fixed option. The chat UI keeps that reply conversational and does not display provider diagnostics or model-source labels. The API replaces free text that suggests an activity or claims to start a session. Chat never creates a session; only the user's selected app button calls the session endpoint. Keep credentials out of logs and evidence.

For a repeatable classroom recording, start the backend with `STILL_SCRIPTED_DEMO=1`. This local-only path uses two fixed replies: `Hi` receives the de-stress follow-up question; asking for a practice then returns the app's Visual Anchor suggestion. It makes no Gemini request. The interface presents the response as “Still” without a source label. Unset the flag to return to the configured provider path.
