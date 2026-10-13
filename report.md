# Assignment 3.1 - Research and Design

## Project and checkpoint

Project: Still, a proposed local meditation-skills prototype.

Repository URL: https://github.com/treyfoerster41-creator/Assignment-3

Assignment 3.1 design checkpoint commit: to be recorded after the reviewed checkpoint is created.

Milestone: Assignment 3.1 Research and Design, due October 15, 2026, at 11:59 PM Eastern.

## What I designed

I designed Still as a general meditation experience with two short guided practices from the assignment: 4-in/6-out paced breathing and 5-4-3-2-1 sensory grounding. The user sees a small choice before practice, then follows one skill one step at a time. The target duration is 70 seconds for breathing and an estimated 78 seconds for grounding. Those are design calculations, not measured application results.

I used the study findings supplied with the assignment to make decisions about short sessions, choice, stopping, emotional effort, personalization, persistent safety access, and low-stimulus language. The full R1-R4/D1-D6 mapping, interface research, flow, technology choices, data plan, limitations, and unresolved decisions are in [the design note](docs/application-design.md). The [early mockup](docs/early-mockup.svg) shows a proposed start screen, one-step breathing screen, and saved-history view.

## Technology and planned data

I plan to use Vue for the interface, FastAPI for validation/model requests/persistence, and SQLite for local fictional conversations and exercise records. I propose a backend-only Gemini connection for optional check-ins or reflections. The model will not generate skill steps, control exercise state, or access the database directly. The app will keep a crisis-support route visible and independent of any model decision.

The folder map and current status are in [README.md](README.md); project boundaries are in [AGENTS.md](AGENTS.md). I used Codex assistance for the research synthesis and document/mockup drafts; see [AI-USE.md](AI-USE.md). The curated prompt and evidence records are [here](prompts/001-assignment3-part1-design.md) and [here](evidence/evidence-log.md).

## What is complete and what remains

This checkpoint contains research notes, a design proposal, an early static mockup, a planned folder structure, and project instructions. It does not contain a working frontend, backend, SQLite schema, model integration, or browser-tested behavior. The Gemini model ID, exact crisis phrase rule, and grounding timing assumptions remain unresolved. Those limits are recorded in [the current handoff](handoffs/current.md). I reviewed the Part 1 files in VS Code before the checkpoint commit.

No recording is included because this is the research/design checkpoint and the supplied Part 1 directions do not require a working-app demonstration recording. No manual application behavior is claimed.
