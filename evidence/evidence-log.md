# Assignment 3 evidence log

This log records the research/design evidence available at the 3.1 checkpoint. It does not claim working behavior.

| Date | Source or check | Expected | Observed | Design decision / limitation |
| --- | --- | --- | --- | --- |
| 2026-10-13 | Assignment 3 overview and supplied R1-R4/D1-D6 table | Use the course table and preserve its meaning; keep counts in context. | The screenshot contains four requirements and six principles, with mention counts and observations across the instructor-described study. The assignment says counts locate findings and do not measure clinical effectiveness. | Transcribed all ten rows into `docs/application-design.md`. I did not access participant-level data or make efficacy claims. |
| 2026-10-13 | Calm breathing-controls help page | Identify a useful breathing interaction pattern and its limits. | The page describes a visual breathing cue, multiple styles, adjustable pace, and timer controls. | Adopt a clear visual cue and pre-start choice; keep the required 4/6 cadence fixed and do not copy marketing claims. |
| 2026-10-13 | Headspace practice catalog | See how short breathing/grounding practices are grouped and presented. | The page groups practices into categories and lists one-minute visual activities alongside a much larger catalog. | Use the broad meditation framing, with only two course-backed choices in this prototype; do not reproduce its content or catalog. |
| 2026-10-13 | MDN `prefers-reduced-motion` reference | Confirm a platform mechanism for a static alternative. | MDN documents the reduced-motion media preference. | Plan a static count display and respect the device preference. No implementation check yet. |
| 2026-10-13 | Official 988 Lifeline | Identify an official U.S. resource source. | The official site provides call, text, and chat support information. | Keep access independent of model/backend behavior; recheck wording and links before implementation. |
| 2026-10-13 | `xmllint --noout docs/early-mockup.svg` | Confirm the mockup file is well-formed XML after relocation. | Command exited successfully. | This does not establish accessibility, visual quality, or browser behavior. A student visual review remains. |
| 2026-10-13 | Student VS Code review | Review the Assignment 3.1 files before creating the checkpoint. | The student reports reading through the files in VS Code and accepting them for commit. | This is a document/code review, not an application run or browser verification; no working app exists yet. |

## Revised approach

An early draft, based only on the pasted overview, mislabeled D1 as a warning about distress detection. The supplied screenshot showed that D1 is “Progressive interface contraction”; the study says the system does not establish how rising distress would be detected or what should contract. I corrected the design mapping: the exercise view stays focused by default, any simpler view is user-controlled, and no distress detector is proposed. This correction is reflected in the design note and mockup rationale.

All web research and document drafting in this log used Codex assistance. The student supplied the assignment material and chose a general meditation scope. No application test is recorded because no working app exists yet. Future evidence should identify whether each result is a mock, live-model response, automated check, or manual browser/database observation.
