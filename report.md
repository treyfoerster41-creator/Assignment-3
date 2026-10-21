# Assignment 3.2 — Working Application and Safety

I built **Still**, a local coursework prototype for a short breathing meditation. I reviewed the final project files in VS Code and accepted them for this submission. This report describes what I built, what I checked, and what I have not verified yet.

## Project and submitted version

Repository: [Assignment-3 on GitHub](https://github.com/treyfoerster41-creator/Assignment-3)

Part 2 implementation commit: **Will be added after the implementation commit is pushed.**

I kept my Assignment 3.1 design report in the [Part 1 archive](https://github.com/treyfoerster41-creator/Assignment-3/blob/main/docs/assignment-3-part-1-report-archive.md). This report is for Part 2; I have not uploaded it to Canvas.

## What I built

I focused this version on one course skill: six cycles of a four-second inhale and six-second exhale. The guided sequence takes 60 active seconds. One tap starts it, and the visual cues advance automatically. I kept Pause, Resume, End practice, and Crisis support available throughout. A pause does not count toward the active time, and the app never forces someone to finish or leave.

I added optional spoken inhale and exhale prompts. They are off by default, use browser speech synthesis when supported, do not use a microphone, and leave the visible cue in place. I also added a user-controlled reduced-motion option.

I kept the optional fictional check-in separate from the exercise. The Vue app sends it through FastAPI; FastAPI handles the model request and saves the conversation in SQLite. This project has no Gemini key configured, so the browser displayed a fixed response labeled as a demo. I did not make a live Gemini request. A limited phrase rule can open the Crisis support panel, but it is not a distress detector. When that rule matches, the triggering text is not saved or sent to Gemini.

The Crisis support panel is available independently of the API and model. It lists U.S. 911 and [988 call, text, and chat options](https://988lifeline.org/contact-us/). The prototype does not place calls or send messages.

I did not implement the 5-4-3-2-1 grounding proposal, saved skill preferences, or recommendations based on earlier sessions. That leaves the user with less skill choice than I proposed in Part 1, but keeps this version focused on a single skill.

## Why I made these choices

The supplied R1 finding says attention dropped for some participants after 90–100 seconds and that around 60 seconds felt comfortable. I set the active breathing sequence to one minute and measured the six cycles in the browser. Setup time and any user-chosen pause are separate from that active duration.

R2 and D4 emphasize easy-to-reach safety information. I kept Crisis support visible on every screen and made its panel independent of Gemini and FastAPI. R3 and R4 emphasize permission to stop and user control. I kept Pause, Resume, and End practice available, and the history records an early exit neutrally. D2 and D3 inform my one-cue-at-a-time flow and the absence of required writing or mood disclosure. D6 informs the restrained motion and plain language.

D1 does not establish how an app could detect rising distress or what it should change. I did not add a distress detector or inferred interface contraction. The user can choose reduced motion directly; in my local browser check, the static-cue class changed immediately when I used that control. D5's personalization goal is still unfinished: I do not save a preferred skill or make recommendations based on prior use.

## What I checked

I ran the backend unit suite: all 8 tests passed. I also ran the frontend production build successfully and checked the patch for whitespace errors. The tests use fictional inputs, temporary databases, and mocked model responses; they do not verify a live Gemini response or clinical effectiveness.

I used Codex's in-app browser for the local checks on October 21, 2026. I checked the unavailable-server message, Crisis support while the API was stopped, a fictional demo reflection, pausing and ending early, a full one-minute practice, history, and persistence after browser refresh and FastAPI restart. I later turned Spoken cues on and completed another one-tap practice without further interaction. The database still contains the original demo records; a read-only inspection found one fictional conversation and three sessions (two completed and one ended early). I did not clear or reseed it.

I cannot confirm from my browser checks that the optional spoken cues were audible to a person. I also have not completed a formal accessibility audit, opened the external Crisis links, or reviewed the database in a database GUI. Those checks are separate from the automated tests and are not claimed as student observations.

## Project files and evidence

- [Application design and research mapping](https://github.com/treyfoerster41-creator/Assignment-3/blob/main/docs/application-design.md)
- [Verification evidence log](https://github.com/treyfoerster41-creator/Assignment-3/blob/main/evidence/evidence-log.md)
- [AI-use disclosure](https://github.com/treyfoerster41-creator/Assignment-3/blob/main/AI-USE.md)
- [Run instructions](https://github.com/treyfoerster41-creator/Assignment-3/blob/main/README.md)
- [Curated Part 2 prompt and revision record](https://github.com/treyfoerster41-creator/Assignment-3/blob/main/prompts/002-assignment3-part2-implementation.md)

I have not made a Part 2 recording or uploaded this report to Canvas. The later integration/evaluation milestone includes the broader scenario evaluation and demonstration/process recording.

## Limits

Still is a coursework software prototype for fictional scenarios only. It is not mental health care, does not diagnose or provide therapy, and does not imply that anyone is monitoring the page. My checks establish local software behavior with mocks and the browser interactions described above; they do not establish that the exercise is clinically effective or suitable for real-world support.
