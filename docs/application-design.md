# Still — Assignment 3 design and implementation notes

Updated November 2, 2026. The Assignment 3.1 proposal and Part 2 implementation note are retained below as historical checkpoints. The current implementation and root `report.md` are for Assignment 3.3.

## Assignment 3.3 implementation update

I kept the two course-provided scripts unchanged: paced breathing (six 4-in/6-out cycles, 60 seconds) and 5-4-3-2-1 sensory grounding (five 15-second prompts, 75 seconds). At the student's later request, I added three short app-authored options: visual anchor, sound noticing, and support points. Each new option has three fixed prompts at 15 seconds each. I do not attribute those additions to the course or its study. The screen advances prompts without typing or another tap. All five can be paused, ended, or left for Crisis support. Optional browser speech is off by default, requires no microphone, and leaves visible instructions in place.

I added a separate Profile page. It saves a local display label, the most recent practice the person deliberately started, and Gemini, demo, or local-fallback recommendations attached to a profile. Profile-linked practice and conversation history remain visible in History. The profile label is not included in Gemini context. A user may switch profiles, delete a profile and its recommendations, or clear history while keeping profile labels. These are local records, not accounts or secure cloud storage; the interface asks for fictional names and warns against saving real health details.

The model adapter asks Gemini for a short conversational reply and one ID from a five-option schema. It is prompted to keep a stated de-stress goal in view when a conversation briefly wanders, then gently point to the separate suggestion card just below its reply. I moved the card beside the latest response so the user does not have to hunt for it. FastAPI checks the ID against the fixed catalog. Model text cannot supply exercise steps or timing, start a practice, write database rows directly, choose a page, or control Crisis support. The user alone starts a session with the practice button.

When Gemini is not configured, the app labels its deterministic rules and replies as demo mode. When a configured live request fails or returns unusable output, local rules can still select one of the five fixed options using the fictional message, recent goal, and permitted activity history. The chat and card label that option as a local fallback, not a Gemini choice. A server exception outside that selection path still returns a no-recommendation fallback. The latest live request has not been retested after these chat and fallback changes.

The backend migration expands saved exercise IDs to the five-option catalog and adds a transparent fallback source for recommendations. It copies existing profile, conversation, session, and recommendation rows. Automated migration checks use temporary databases; the production database was not cleared or reseeded.

I ran 18 distinct fictional messages through the app's deterministic mock selection and verified the saved recommendation for each. Additional invariants check that generated IDs outside the five fixed options are suppressed, that a recommendation does not start a practice until the user chooses, and that a limited crisis phrase bypasses the model and does not store the triggering text. A separate simulated provider failure confirms that an explicitly labeled local fallback option can be saved without creating a session. These are software checks, not participant research or evidence that Gemini will return the same choices.

One unexpected test result showed why profile context matters: a vague “short exercise” prompt inherited the preceding grounding recommendation when I initially reused one profile across all scenarios. I isolated the 18 cases so each measured its own request, and kept a separate check that a vague follow-up can use recent profile activity. This is an implementation observation, not a finding about people or clinical outcomes.

An untested limitation is how the grounding prompts work for someone who cannot or does not want to use a particular sense, especially smell or taste. The screen now says the person may let a prompt pass, but the fixed sequence does not offer an alternate sense prompt or a skip button. The three app-authored additions are brief design prototypes, not user-tested skills or evidence-based claims. I have not conducted a user study, a formal accessibility review, or a live Gemini check of the latest goal-bridging prompt. The course's R/D findings still guide the relevant design constraints: keep the core skill short (R1), safety easy to reach (R2/D4), stopping voluntary (R3), the user in control (R4), one action/prompt at a time (D2), low emotional cost (D3), restrained language/motion (D6), and personalize only from light optional history (D5). D1 does not establish a way to detect rising distress, so the app makes no such inference.

Google's official [Gemini model documentation](https://ai.google.dev/gemini-api/docs/models) and [structured output documentation](https://ai.google.dev/gemini-api/docs/structured-output) describe the model listing and JSON-schema response mode used here. Checked November 2, 2026. A separate direct request and an end-to-end fictional browser chat succeeded with `gemini-3.6-flash` before the current goal-bridging and fallback changes; these earlier live checks are recorded separately from mocked transport tests in the [evidence log](../evidence/evidence-log.md).

## Assignment 3.2 implementation update — historical checkpoint

The student asked to begin Part 2 and keep the breathing/meditation program as the focus. I narrowed the first working version to one complete course skill: six cycles of a four-second inhale and six-second exhale. The app does not implement the 5-4-3-2-1 practice yet. That is a scope reduction from the Part 1 proposal, not a claim that grounding is complete.

The active exercise is 60 seconds from the first breathing instruction to the sixth exhale. Choosing the practice and waiting for the session-start API response are entry/setup and are reported separately. A user-selected pause stops the active timer; the user can resume or end early. A background tab pauses the practice. Reloading or closing during an unfinished practice records it as interrupted when the app is opened again. No timer forces a choice or navigation.

The exercise advances automatically after one start action. Optional browser speech synthesis can speak the current inhale/exhale cue; it is off by default, does not use a microphone, and leaves the same visible text and shape available. If the browser lacks speech synthesis, the app explains that visual cues remain available. Speech is canceled when the exercise pauses or ends. The control adds no required interaction once practice begins.

The optional check-in remains outside the exercise. FastAPI sends a bounded recent conversation and the current fictional message to Gemini, then persists the user and assistant messages. The system instruction limits the reply to a short, neutral reflection and prohibits diagnosis, therapy claims, advice, or new skill steps. The Vue app owns the exercise script and timer; the model cannot select the page, change breathing counts, write to SQLite, or decide whether Crisis support is visible. With no `GEMINI_API_KEY`, the app shows a fixed response labeled as a mock. A live request failure receives a fixed, sanitized fallback. At the Part 2 checkpoint no key had been configured; Part 3 later added one, but live checks have returned HTTP 503 or timed out.

The model ID is `gemini-3.8-flash`, using Google's documented `generateContent` REST API through backend HTTPX with the API key in the `x-goog-api-key` header. The model and REST pattern were checked against [Google's model list](https://ai.google.dev/gemini-api/docs/models) and [text-generation documentation](https://ai.google.dev/gemini-api/docs/generate-content/text-generation) on October 21, 2026. The live integration is optional and not yet verified with a key.

The header and footer keep a Crisis support control available on every view. Its panel is bundled in the frontend and does not depend on FastAPI, Gemini, or phrase matching. It links to [official U.S. 988 call, text, and chat information](https://988lifeline.org/contact-us/) and 911 for immediate danger. A small explicit phrase list can also route an optional chat message to that panel. This is limited routing, not distress detection; it can miss paraphrases or match quotations. When it matches, the triggering text is neither sent to Gemini nor saved. SQLite stores only that the fixed panel was displayed.

The Part 2 scope and dependencies were approved by the student on October 21, 2026. The implementation uses Vue 3.5.44, Vite 8.3.5, `@vitejs/plugin-vue` 6.0.10, FastAPI 0.156.8, Uvicorn 0.53.0, and HTTPX 0.28.1. Install results and build/runtime checks are recorded in the evidence log. Future dependency additions still require the student's approval.

The local app was exercised in Codex's in-app browser on October 21. The 60-second run reached six cycles and saved as completed; a paused early exit saved its actual progress; mock reflection and history also appeared. Refreshing the browser and restarting FastAPI preserved the saved records. Stopping FastAPI produced a clear start error while the bundled Crisis support panel still opened. Optional speech synthesis was added afterward; the browser exposes the feature, but the agent cannot confirm that a person can hear its output. Student listening/acceptance is still needed. These are agent-run local checks, not student review. Automated checks and remaining gaps are in [the evidence log](../evidence/evidence-log.md).

Part 2 does not implement sensory grounding, history personalization, or a live Gemini response. One fixed skill and an optional check-in reduce setup effort, but they offer less skill choice than the Part 1 proposal. The live integration is unverified because no key is configured. No clinical or effectiveness claims are made.

## Part 1 design proposal (historical)

The sections below preserve the Part 1 reasoning and planned alternatives. Where they differ from the current app, the dated Part 2 implementation update above is authoritative.

## What I want to make

I want the application to feel like a small meditation space, with general meditation as the framing rather than breathing as the whole product. The first two guided practices will be paced breathing and noticing the surroundings through 5-4-3-2-1 grounding. Both remain the exact course skills. The user gets a small choice between them, then sees one instruction at a time. I am not adding a large library of model-generated meditation or therapeutic exercises.

The working name is **Still**. The application will identify itself as a localhost coursework skills prototype, with fictional scenarios only. It will make no diagnosis, therapy, monitoring, or clinical-effectiveness claim.

The intended first screen asks one simple question, such as "What might feel useful right now?", and offers two short choices: breathing meditation or sensory grounding. This preserves a meaningful choice without turning the home screen into a catalog or dashboard. A previously chosen practice can be gently suggested, with the other choice still visible. History, preferences, and an optional fictional check-in stay easy to reach. Someone can begin without writing a message or waiting for Gemini.

## Two planned practices

| Practice | Fixed course skill | Presentation | Intended exercise time |
| --- | --- | --- | --- |
| Guided breathing meditation | Inhale for four, exhale for six; six cycles | A modest expanding/contracting circle with the phase label and count. A static count view carries the same pace when motion is reduced. | 70 seconds: 5-second opening, 60 seconds of cycles, 5-second closing. |
| Notice your surroundings | Five things seen, four felt, three heard, two smelled, one tasted, in that order | One sensory prompt at a time. The user identifies things privately and presses Next; no typed list is required. | 78-second planning assumption: 4-second opening, 10 seconds reading five prompts, 60 seconds identifying 15 items at four seconds each, 4-second closing. |

These are estimates for design, not measured outcomes. Setup, optional chat, and selecting a practice happen before the first exercise instruction and are reported separately. User-chosen pauses and time accessing crisis information are excluded from active exercise time. The final card stays until the user chooses where to go; a timer never forces the person out.

Grounding's pace is an explicit assumption, not a guarantee that everyone will identify something in four seconds. A user may stay on a prompt, pause, skip an unavailable sense with a recorded skip, or leave. Skipping is not silently labeled completion of the full skill. Both planned sequences leave room below the 90-second assignment limit. Later browser checks will measure from the first instruction through the final planned step, including any application delay.

## Main flow and screen states

```mermaid
flowchart TD
    A[Home: choose meditation] --> B[Setup: visible preferences, optional check-in]
    B --> C[Start chosen fixed practice]
    C --> D[One instruction at a time]
    D --> E[Closing card and optional reflection]
    E --> F[History: sessions and conversations]
    D --> P[Pause: resume or leave]
    P --> D
    P --> X[Ended early: save actual progress]
    B --> M[Optional Gemini message]
    E --> M
    M --> R[Reply or clear request failure]
    R --> B
    A -. always accessible .-> H[Crisis-support information]
    D -. always accessible .-> H
    P -. always accessible .-> H
    F -. always accessible .-> H
    R -. always accessible .-> H
```

The [early screen sketch](early-mockup.svg) shows the proposed two-choice start, breathing exercise, and history from Part 1. It remains a static mockup; it does not represent the current single-practice implementation.

- **Home/setup:** short prototype description, one compact choice between the two practices, optional check-in, preferences, History, and Crisis support. The last chosen practice can be suggested, but it does not automatically start. There is no large skill library or mood questionnaire.
- **Exercise:** one large instruction, a phase/count or sensory prompt, progress, Pause, End practice, and Crisis support. Chat is not layered over the exercise. No required text entry.
- **Paused/interrupted:** progress stops; Resume and End practice remain available. Moving the tab into the background will pause rather than catching up and silently completing the exercise. Refresh will show that an unfinished session was interrupted; it will not restart motion without a choice.
- **Closing:** optional one-tap feedback (helpful, neutral, not helpful, or skip). There is no required mood score or claim that the exercise improved someone.
- **History:** date, practice, completed/ended-early/interrupted status, active duration, and any optional reflection. Conversation transcripts are accessible from the same history area. Empty history has a clear first-practice action.
- **Failures:** a model error leaves the fixed practice available; a save error says the record has not been saved and offers retry. There is no invented successful reply or saved record.

## Model role and relevant context

The application demonstrates an optional conversational reflection and persisted conversation records, although the current response is a fixed mock because no live key is configured. Chat is not a prerequisite for the breathing practice.

The backend integration targets Google Gemini model `gemini-3.8-flash` for short fictional check-ins. The exact model ID and REST pattern were checked against Google's official documentation on October 21, 2026. The optional prompt asks for a short, neutral reflection; it disallows diagnosis, therapy claims, advice, or new skill steps. A fixed application response is used when no key exists or a provider request fails. The model does not change the breathing cadence, navigate, write to SQLite, or generate database queries. No live Gemini response has been observed.

FastAPI owns validation, the bounded recent conversation, model calls, and all writes. User messages are limited to 500 characters and recent conversation context to six messages. The current prompt and fallback behavior are implementation choices, not clinical validation.

Model calls complete outside the exercise sequence. A timeout or provider failure produces a fixed application fallback. Credentials stay in a backend-only ignored `.env`; this project currently has no `.env` or configured key.

## Personalization and user control

Part 1 proposed a gentle suggestion based on a prior choice, alongside editable display preferences. Part 2 implements user-controlled reduced motion and optional spoken cues; neither is used to infer a preferred skill or personalize a recommendation. The 4/6 cadence remains fixed.

Remembering a choice could reduce repeated setup, but a prior choice could be wrong for the next session. That tradeoff remains unresolved because Part 2 does not persist practice preferences. The app does not infer distress from typing speed, sentiment, pauses, or diagnosis. There are no streaks, rewards for continuing, or penalties for leaving.

The user can review and delete saved fictional conversations and sessions. Deleting history will not silently reset explicit display preferences; Reset preferences is a separate control. No account or real personal identity is needed for this local demonstration. Every screen uses low-stimulus, nonjudgmental language; the app does not use clinical phrasing, forced positivity, or language that treats leaving early as failure.

## Crisis-related input and independent access

Every application screen includes a clearly labeled Crisis support control, including while an exercise is active or paused. It opens a locally bundled information panel without Gemini, phrase matching, or a backend request. The panel links to the official [988 Lifeline](https://988lifeline.org/) call, text, and chat options, and includes a 911 link for immediate danger. External calls and links require a compatible device or connectivity.

The prototype will not initiate a call, contact another person, or imply that someone is watching the conversation.

An optional chat message that matches a small explicit phrase list receives a fixed application message and the same resource panel. This is limited routing, not a clinical detector; it can miss wording or match a fictional quotation. The triggering text is not sent to Gemini or stored. The application may store only that it displayed the fixed resource response. Automated mock checks cover this rule; its sensitivity and completeness are not established.

## Architecture and information saved

| Part | Responsibility |
| --- | --- |
| Vue | Screen state, exercise timing and pacing cues, explicit preferences, pause/exit controls, chat state, history rendering, and locally bundled support panel. |
| FastAPI | Input validation, fixed skill definitions/versioning, bounded Gemini requests, application-owned persistence, history endpoints, and sanitized failures. |
| SQLite | Fictional preferences, conversations, messages, session progress/status, and optional feedback. No hotel records or clinical diagnosis fields. |

### Technology decisions and current status

- **Vue** currently presents one fixed practice, one-step breathing cues, pause/exit controls, optional check-in, saved history, and the independent crisis panel. The second Part 1 practice is not implemented.
- **FastAPI** validates requests, serves fixed skill steps and support information, supplies bounded context to the model, and performs all persistence. Keeping model calls and credentials on the backend also prevents a model response from taking over exercise timing or navigation.
- **SQLite** provides durable local conversations and exercise history without setting up a remote database. A single fictional local profile is enough for this course prototype; users can inspect and delete their saved records.
- **Gemini through a backend-only request** is implemented as an optional path using HTTPX. It requires a student-configured backend-only key; without one, the response is a fixed mock. The core practice and crisis-support panel work without Gemini.

The required localhost stack has been installed and exercised locally. One fictional Gemini 3.6 response has been verified end to end; see the evidence log. A formal accessibility review remains unverified.

Planned storage uses one fictional local demo profile, not authentication:

| Table | Proposed fields and purpose |
| --- | --- |
| preferences | profile ID, last practice, text mode, motion preference, updated timestamp. Explicit choices only. |
| conversations | ID, fictional profile ID, created/updated timestamps. Groups the saved exchange. |
| messages | ID, conversation ID, user/assistant role, text, timestamp, reply status, and live/mock/fixed source. Failed requests remain identifiable. |
| exercise_sessions | ID, practice and script version, start/end, completed/ended-early/interrupted status, last step/cycle, active/paused/wall-clock duration, and optional feedback. |

Saving events uses stable IDs and transactions so a retry does not create duplicate sessions. The interface confirms saved status only after backend acknowledgement. Model context includes only relevant recent records, not the full database. When a limited crisis phrase rule matches, do not save the user's triggering text; the conversation may record only that the fixed resource response was shown.

## Proposed project organization and reuse

I chose a separate project folder: `/Users/treyfoerster/IST 402/Assignment 3`. It has its own documentation and planned frontend/backend areas, with the repository at [Assignment-3 on GitHub](https://github.com/treyfoerster41-creator/Assignment-3). Any future database and `.env` will be local to this project and ignored; no travel data, database, or credential has been copied here.

```text
Assignment 3/
  frontend/              Vue screens and deterministic exercise controls
  backend/
    app/                 FastAPI, fixed skill content, Gemini adapter, persistence
    tests/               Fictional fixtures and mocked behavior checks
    data/                Ignored local skills database
  docs/                  Design, early mockup, research findings and decisions
  evidence/              Dated expected/observed checks and selected failure evidence
  prompts/               Curated instructions and revisions
  handoffs/current.md    Actual state and next implementation task
  README.md              Current milestone, structure, eventual run instructions
  AGENTS.md              Project-specific boundaries and verification rules
  AI-USE.md              Tools, known model identifiers, and roles
  report.md              First-person current milestone submission
  .env.example           Key-free configuration template
  .gitignore             Credentials, local database and generated files
```

I can reuse the course's Vue loading/error-state patterns, FastAPI/HTTPX Gemini transport and safe configuration, SQLite transactions, and mock-provider test patterns. Conversation/session storage, the fixed exercises, and history UI are new. I am not reusing hotel-generated SQL, Geoapify, booking tables, or the existing travel database for this app.

## Research findings and design decisions

The assignment's study table describes coded mentions across 15 participants. I use its counts as evidence of what this class study emphasized, not as proof of clinical benefit or as population-wide statistics. The design decisions below translate each finding into a prototype choice and note where the evidence leaves a question open.

| Code | Finding and reported observation | Design decision for Still |
| --- | --- | --- |
| R1 | Skills longer than 90-100 seconds lose people. Around 60 seconds felt comfortable; after 90-100 seconds attention dropped and participants said they might abandon the exercise. The table reports 38 mentions, concentrated on shorter-is-better and paced breathing. | Keep each complete guided sequence below 90 seconds. The breathing sequence is planned for 70 seconds; grounding is estimated at 78 seconds. Treat these as design targets and measure the actual end-to-end exercise later. |
| R2 | Crisis access must be frictionless. The table reports 30 mentions across all 15 participants; participants wanted safety reachable without navigating through screens. | Keep Crisis support visible in every state and make its information open without model or backend access. |
| R3 | The user must be allowed to stop. The table reports 39 mentions and says all 15 participants raised permission to stop or leave without consequence. | Keep Pause and End practice visible during each exercise. Record early exit neutrally; never block it, scold the user, or mark it as failure. |
| R4 | The user controls their own journey. The table reports 68 mentions, including choosing by emotional state; participants wanted options instead of being routed to one practice. | Offer a small, clear choice between breathing and grounding. A previous choice may be suggested, but never starts automatically or hides the other practice. Avoid asking for a mood disclosure. |
| D1 | Progressive interface contraction. The table reports 54 mentions, especially around crisis access and the overall journey. As distress rises, the interface should contain less; the study does not establish how a system would know distress rose or what should contract. | Keep the exercise screen focused by default. If a simpler view is offered, make it a user-controlled display choice, not an inferred distress response. Keep Crisis support visible in either view. |
| D2 | One atomic skill at a time. The table reports 100 mentions across all 15 participants, centered on STOP, cognitive reframe, and paced breathing; participants responded to one action per screen, not a library, menu, or dashboard. | Once a practice starts, show only its current instruction and essential controls. The initial choice is limited to two short practice options; do not build a catalog or combine skills into a single exercise. |
| D3 | Minimize emotional cost. The table reports 148 mentions across all participants, concentrated on breathing and grounding. It defines cost as what is demanded to feel, disclose, or perform. | No required writing, mood score, or explanation. Sensory identification can stay private; check-in and post-practice feedback are optional and skippable. |
| D4 | Persistently visible safety. The table reports 31 mentions, with participants noticing when safety access disappeared inside an exercise. | Keep the same Crisis support control visible on home, exercise, pause, history, and chat screens. |
| D5 | Personalization without configuration burden. The table reports 49 mentions, especially on lightweight feedback and choosing by emotional state; participants wanted adaptation from prior use without setup. | Use the last chosen practice or optional one-tap feedback as a gentle suggestion, with an immediate alternative and a reset/delete control. Avoid a setup questionnaire. Do not infer emotional state from typing, pauses, or sentiment. |
| D6 | Low-stimulus, nonjudgmental language. The table reports 97 mentions across all 15 participants; participants described clinical phrasing as diagnostic, cheerfulness as condescending, and saturated color or motion as demanding. | Use calm contrast, restrained motion, plain instructions, and neutral completion/exit language. Respect reduced-motion settings and avoid clinical labels or forced cheerfulness. |

The main design tension is between R4's desire for choice and D2's one-skill, one-action screens. I resolve it with two compact practice choices before the exercise, followed by a focused single-skill flow. I do not interpret the study's mention counts as a ranking of therapeutic effectiveness.

Additional interface and accessibility research, reviewed October 13, 2026 with Codex assistance:

- [Calm's breathing-control documentation](https://support.calm.com/hc/en-us/articles/360000069973-Calm-Breathing-Exercises-How-to-Adjust-Speed-Timers-Haptics-Vibrations): describes a visual breathing cue and controls before starting. I adopted the idea of a visible pacing cue. Calm also offers multiple styles and adjustable duration/rate; I am keeping the course's fixed four/six cadence and limiting the first screen to two course skills. I will not repeat the source's health-benefit marketing claims.
- [Headspace's practice catalog](https://www.headspace.com/content/topics/videos-and-more/3): groups short activities under breathing, grounding, and meditation categories and includes one-minute visual activities. This supports presenting breathing and sensory awareness within a broader meditation experience. The page also demonstrates how a catalog can grow large; I am keeping this prototype to two skills and original wording rather than copying content or claims.
- [MDN reduced-motion documentation](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion): documents the browser/device preference for reducing motion. I plan a static count alternative and a visible control to reduce motion further.
- [Official 988 Lifeline](https://988lifeline.org/): source for U.S. call, text, and chat support information. The app will link to official options and will not initiate contact on the user's behalf.

The instructor supplied the R1-R4/D1-D6 study summary for this assignment. The directions say its mention counts identify where a finding appeared, not clinical effectiveness; no separate research dataset is expected. I did not conduct clinical research or inspect participant-level data.

## Assignment 3 milestones and current scope

| Milestone | Due | Scope in this plan |
| --- | --- | --- |
| 3.1 Research and Design | October 15, 2026, 11:59 PM Eastern | Completed design checkpoint; report preserved in the archive. |
| 3.2 Working Application and Safety | October 22, 2026, 11:59 PM Eastern | Historical checkpoint: one working breathing practice, optional mock reflection, SQLite history, and independent safety panel. |
| 3.3 Integration, Evaluation, and Demonstration | October 29, 2026, 11:59 PM Eastern | Current implementation includes five fixed practices (two course skills and three app-authored additions), profile-backed recommendations, Gemini integration, eighteen mock scenarios, and behavior checks. After initial 503s on 3.8 and a truncated 3.6 response at the old token cap, the cap was raised and a fictional browser chat returned a live 3.6 response with a grounding recommendation. Later revisions guide replies back to an optional choice, constrain overreaching model text, and keep session start behind the user's button. The current prompt/fallback changes have not had a fresh live check; student review and recordings remain pending. |

## Milestone record and next work

Part 1 established the design, early mockup, model/context boundaries, data plan, research mapping, project instructions, and report. Its report is preserved in `docs/assignment-3-part-1-report-archive.md`.

The student reported a Part 1 VS Code review; the earlier design checkpoint is present in Git history. The Part 2 checkpoint and report are preserved. For Part 3, the next work is to get one successful fictional live Gemini response, review the changed files and app, record the required demo and process screencast, and then add the exact commit and accessible recording links to `report.md`. No Part 3 commit, push, or Canvas upload is claimed.

Part 3's automated checks and one read-only local browser inspection are listed in the evidence log. They do not establish live model behavior, formal accessibility, student review, or class acceptance.

## Open decisions and limits

- Separate Assignment 3 folder is `/Users/treyfoerster/IST 402/Assignment 3`; GitHub repository: [Assignment-3](https://github.com/treyfoerster41-creator/Assignment-3). The name Still is provisional.
- Grounding now runs as a fixed 75-second sequence. The screen lets the user pass on a prompt, but does not offer an alternate sense prompt or button to skip; that limitation has not been user-tested.
- The phrase list is implemented as limited routing, but coverage beyond the checked fictional examples is unknown.
- Gemini model ID `gemini-3.6-flash` is selected in the ignored `.env`. Gemini 3.8 returned HTTP 503; the first 3.6 response was cut off at the old 160-token cap. With a 512-token cap, a fictional direct request and a fictional browser chat both returned valid replies; the browser also displayed a fixed grounding suggestion. See the evidence log for agent-run checks. Student acceptance remains pending.
- The app has optional browser speech synthesis, but a person has not confirmed audibility in the target browser. It has not received a formal accessibility audit or testing in additional browsers.
- The current chat renders a short transcript, handles greetings with an optional preference question, and uses a small fixed rule for suggesting grounding when the fictional message asks to focus on surroundings. Reduced motion forces the breathing orb to one fixed scale; the optional spoken breathing cue is modestly encouraging. Browser voice quality depends on the device, and these latest interactions still need student/browser review.

Current verification: the browser, automated checks, model mode, and local records are detailed in `evidence/evidence-log.md`. A local ignored SQLite database was created with only the fictional demo conversation and two test sessions used for the browser run. The Assignment 2 project and travel data were not changed. Student VS Code/database review, live Gemini testing, a recording, commit, push, and Canvas upload remain unclaimed.
