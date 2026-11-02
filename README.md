# Still — Assignment 3

Still is a local coursework prototype for five short, fixed meditation options. The first two use the course skills; the other three are small app-authored additions requested for this prototype. It is for fictional classroom scenarios only. It is not mental health care, does not diagnose or provide therapy, and does not imply that anyone is monitoring the page.

## Current state — Assignment 3.3

- **Paced breathing:** six fixed cycles of a four-second inhale and six-second exhale (60 seconds). One tap starts the sequence; cues advance without further interaction.
- **5-4-3-2-1 sensory grounding:** five fixed prompts, each shown for 15 seconds (75 seconds total). The screen advances automatically; no typing is required.
- **Three app-authored options:** visual anchor, sound noticing, and support points each use three fixed 15-second prompts. These were added for the prototype; they are not represented as course-provided skills or findings from the supplied study.
- **Optional conversational suggestion:** the backend sends a bounded fictional chat and limited activity context to Gemini and asks for a short reply plus one of five allowed exercise IDs. The server owns all five scripts. It replaces model text that gives activity advice or claims to start a practice. Only a user-selected app button starts a session.
- **Clearly marked demo and fallback behavior:** without a Gemini key, the local mock uses fixed rules and labels its reply as a preset. If a live request fails, local rules can still select one of the fixed options; the reply and suggestion card say this was a local fallback, not a live Gemini choice. A configured key does not guarantee provider availability.
- **Guided conversation:** the chat is prompted to keep a stated goal in view when the conversation wanders, then gently point to the optional exercise card shown immediately below the latest response. The model can choose only one of five fixed IDs and cannot initiate an exercise. The user may try the card, choose another option, or skip it. The earlier live Gemini browser check succeeded before the latest chat changes; the latest prompt/fallback behavior has mock coverage only.
- **Profiles and history:** a local profile label can retain the last practice the person chose, recommendations, and linked fictional conversations and sessions. The profile label itself is not sent to Gemini. Profiles are local labels, not accounts.
- **Safety and access:** Pause, End, and Crisis support remain available during practice. Crisis support is bundled in the interface and does not depend on the API or model. Reduced motion keeps the breathing ball at one fixed size. Optional spoken prompts are slightly warmer and encouraging, use browser speech synthesis, and do not use a microphone; the available voice depends on the device.

Gemini's only application role is to offer a short conversational response and select a fixed exercise ID. It cannot create steps, change timing, start an exercise, route a person, write database records, or control Crisis support. A limited explicit phrase rule can open the Crisis panel; it is not a distress detector and may miss or overmatch language.

Earlier reports remain available: [Assignment 3.1](docs/assignment-3-part-1-report-archive.md) and [Assignment 3.2](docs/assignment-3-part-2-report-archive.md). Root `report.md` is the Part 3 draft.

## Run locally

Use Node.js 20.19+ or 22.12+ and Python 3.10+. From the project root:

```sh
cd frontend
npm install
cd ../backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The frontend uses Vue 3.5.44, Vite 8.3.5, and `@vitejs/plugin-vue` 6.0.10. The backend uses FastAPI 0.156.8, Uvicorn 0.53.0, and HTTPX 0.28.1. Lockfiles and requirements record the installed versions.

Start the backend from `backend/` in one terminal:

```sh
source .venv/bin/activate
uvicorn app.main:app --reload
```

Start the frontend from `frontend/` in a second terminal:

```sh
npm run dev
```

Open <http://127.0.0.1:5173>. The backend API is at <http://127.0.0.1:8000>. SQLite initializes at `backend/data/still.db`; the Part 3 migration expands the allowed fixed-exercise and recommendation-source values while preserving existing records.

## Optional live Gemini configuration

The app works in demo mode without a key. To enable live responses, copy `.env.example` to the project root `.env` and set `GEMINI_API_KEY` there. Keep the value backend-only and out of source control, screenshots, recordings, and chat. The current model is `gemini-3.6-flash`; `GEMINI_MODEL` can override it. The backend uses a bounded JSON schema that permits only the five fixed exercise IDs. Model output never creates or changes exercise instructions. If a request fails or its output is invalid, local rules may suggest a fixed option; the app labels that recommendation as a fallback, not a live Gemini choice. Only the user can start the practice.

## Checks

From `backend/`:

```sh
python -m unittest discover -s tests -v
```

From `frontend/`:

```sh
npm run build
```

Automated checks use temporary databases, fictional inputs, and mocked transport/model responses; they do not prove live Gemini behavior. A separate single fictional live response was observed in this session, as recorded in [the evidence log](evidence/evidence-log.md). Neither automated nor live checks establish clinical benefit, accessibility conformance, consistent provider availability, or student review.

## Key files

| Path | Purpose |
| --- | --- |
| `frontend/src/App.vue` | Practice, profile, chat suggestion, history, accessibility controls, and independent Crisis panel |
| `backend/app/main.py` | FastAPI validation, exercise/session rules, profile/history persistence, and model boundary |
| `backend/app/model.py` | Gemini REST adapter and clearly labeled mock/fallback behavior |
| `backend/app/exercises.py` | The five fixed exercise definitions; first two are course skills, last three are app-authored |
| `backend/tests/fixtures/assignment3_part3_scenarios.json` | Eighteen fictional scenario inputs and expected choices |
| `docs/application-design.md` | Research grounding and dated design decisions |
| `evidence/` | Separate expected/observed automated, live, and manual evidence |
| `prompts/` | Curated implementation and revision notes, not a full chat export |
| `report.md` | First-person Assignment 3.3 submission draft; final links and student evidence remain pending |

Never offer, deploy, or recommend this local coursework prototype as support for someone in distress. Use fictional scenarios only; do not enter real identities or real distress narratives.
