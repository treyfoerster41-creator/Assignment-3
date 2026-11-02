# Still backend

FastAPI owns request validation, the fixed exercise catalog, SQLite persistence, bounded Gemini requests, and safe fallback behavior. Run it from this directory with the project-local environment active:

```sh
source .venv/bin/activate
uvicorn app.main:app --reload
```

The local database is `data/still.db`. Initialization applies additive migrations for Part 3 profiles, linked history, and recommendations. Existing conversation and session rows are preserved. Tests use temporary databases and mock the model transport; they never require a real key.

To enable Gemini, place `GEMINI_API_KEY` in the ignored project-root `.env`. The key is loaded by the backend only. The app defaults to `gemini-3.6-flash`, uses HTTPX with a finite timeout, and accepts only a completed structured reply plus one of five fixed exercise IDs. The first two scripts are course skills; visual anchor, sound noticing, and support points are app-authored additions. A 512-token output cap leaves room for Gemini's thinking tokens. If a request fails or output is invalid, the backend can use local rules to offer one fixed option and labels it as a fallback rather than a live Gemini choice. The API replaces free text that suggests an activity or claims to start a session. Chat never creates a session; only the user's selected app button calls the session endpoint. Keep credentials out of logs and evidence.
