# Still — Assignment 3

Still is a local coursework prototype for practicing a short, fixed paced-breathing meditation. It is for fictional classroom scenarios only. It is not mental health care, does not diagnose or provide therapy, and does not imply that anyone is monitoring the page.

## Current state

- Assignment 3.2 working-app scope: one complete 4-in/6-out breathing practice, optional short model reflection, persistent conversation/session history in SQLite, and a standalone Crisis support panel.
- The exercise contains six four-second inhales and six six-second exhales (60 seconds total). Pause time is excluded; the application never forces completion or exit.
- One tap starts the practice. The six cycles and visual cues advance automatically, so no screen interaction is required while breathing; pause, end, and Crisis support remain available.
- Optional spoken inhale/exhale cues are off by default, use browser speech synthesis when supported, and never replace the visible prompt. No microphone is used. The reduced-motion control applies immediately without a reload.
- Part 1 also proposed 5-4-3-2-1 grounding. That second skill is not implemented or claimed in this milestone.
- The app runs without credentials using a clearly labeled fixed mock response. Live Gemini requests require a backend-only key in the ignored root `.env`.
- Design rationale and changes since Part 1 are in [the design note](docs/application-design.md). The [early mockup](docs/early-mockup.svg) remains a static proposal.
- The current Part 2 submission draft is [report.md](report.md); the Part 1 report is preserved in [the archive](docs/assignment-3-part-1-report-archive.md).

## Project map

| Path | Purpose | Current status |
| --- | --- | --- |
| `frontend/` | Vue practice, optional reflection, history, and crisis panel | Implemented; build and browser checks are recorded separately |
| `backend/app/` | FastAPI routes, Gemini adapter, phrase routing, and SQLite persistence | Implemented; automated checks use mocked model responses |
| `backend/data/still.db` | Local SQLite history | Created automatically and ignored by Git; contains only local demo records |
| `docs/application-design.md` | Part 1 research plus Part 2 implementation decisions | Updated October 21, 2026 |
| `docs/early-mockup.svg` | Early interaction sketch | Static design artifact |
| `prompts/` | Curated project instructions and revisions | Part 1 and Part 2 records |
| `evidence/` | Expected/observed checks and decisions | Automated and browser observations are kept distinct |
| `handoffs/current.md` | Truthful project state and next task | Current as of October 21, 2026 |
| `AGENTS.md` | Project-specific boundaries and safety rules | Active instructions |
| `AI-USE.md` | AI tools, versions, and roles | Updated for Part 2 |
| `report.md` | Assignment 3.2 Canvas submission | Draft until student review, exact commit, and remaining observations are recorded |

## Setup

Use Node.js 20.19+ or 22.12+ and Python 3.10+. From the project root:

```sh
cd frontend
npm install
cd ../backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The frontend uses Vue 3.5.44, Vite 8.3.5, and `@vitejs/plugin-vue` 6.0.10. The backend uses FastAPI 0.156.8, Uvicorn 0.53.0, and HTTPX 0.28.1. `package-lock.json` and `requirements.txt` record the dependency set.

## Run locally

Start the backend from `backend/` in one terminal:

```sh
source .venv/bin/activate
uvicorn app.main:app --reload
```

Start the Vue interface from `frontend/` in a second terminal:

```sh
npm run dev
```

Open <http://127.0.0.1:5173>. The API is at <http://127.0.0.1:8000>. SQLite initializes automatically at `backend/data/still.db`; it is not reseeded and survives app or server restarts.

The app runs without a live model key. To enable Gemini, copy `.env.example` to the project root as `.env` and add a `GEMINI_API_KEY` obtained by the student. The current configured model is `gemini-3.8-flash`. The key stays in the backend and must never be committed or copied into the frontend. When no key exists, the app labels the response as a preset demo response. When a configured request fails, it stores and displays a fixed fallback without exposing provider errors.

## Repeatable checks

From `backend/`:

```sh
python -m unittest discover -s tests -v
```

From `frontend/`:

```sh
npm run build
```

Automated tests use fictional text, a temporary SQLite database, and a mock model provider. They do not establish live Gemini behavior or student manual browser/database review.

## Safety and data

The Crisis support control is bundled into every view and does not call FastAPI or Gemini. It links to U.S. 988 call, text, and chat options; external links require internet or a compatible device. A limited phrase rule in the optional chat route may show this same panel, but it is not a distress detector and can miss or overmatch wording. Matched input is not sent to Gemini or saved; history records only that the fixed panel was shown.

Use fictional scenarios only. Do not offer, deploy, link, or recommend this coursework prototype as support for a person in distress. Never include real identities, private conversations, API keys, or `.env` contents in repository files or evidence.
