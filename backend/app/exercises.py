"""Fixed practice catalog. Gemini may choose an ID, never alter a script."""

from __future__ import annotations

from typing import Any


BREATHING_ID = "breathing-4-6"
GROUNDING_ID = "grounding-54321"
VISUAL_ANCHOR_ID = "visual-anchor"
SOUND_NOTICING_ID = "sound-noticing"
CONTACT_POINTS_ID = "contact-points"

EXERCISES: dict[str, dict[str, Any]] = {
    BREATHING_ID: {
        "id": BREATHING_ID,
        "name": "Paced breathing",
        "short_name": "In for four, out for six",
        "begin_label": "Begin breathing",
        "description": "Six fixed cycles of a comfortable four-second inhale and six-second exhale.",
        "kind": "cycles",
        "duration_seconds": 60,
        "cycle_count": 6,
        "inhale_seconds": 4,
        "exhale_seconds": 6,
        "script_version": "1.0",
    },
    GROUNDING_ID: {
        "id": GROUNDING_ID,
        "name": "5-4-3-2-1 sensory grounding",
        "short_name": "Notice your surroundings",
        "begin_label": "Begin grounding",
        "description": "Five fixed sensory prompts, one at a time; nothing needs to be typed.",
        "kind": "steps",
        "duration_seconds": 75,
        "step_seconds": 15,
        "steps": [
            {"count": 5, "sense": "see", "cue": "Notice five things you can see."},
            {"count": 4, "sense": "feel", "cue": "Notice four things you can feel."},
            {"count": 3, "sense": "hear", "cue": "Notice three things you can hear."},
            {"count": 2, "sense": "smell", "cue": "Notice two things you can smell."},
            {"count": 1, "sense": "taste", "cue": "Notice one thing you can taste."},
        ],
        "script_version": "1.0",
    },
    VISUAL_ANCHOR_ID: {
        "id": VISUAL_ANCHOR_ID,
        "name": "Visual anchor",
        "short_name": "Focus on one object",
        "begin_label": "Begin visual anchor",
        "description": "Three gentle 15-second prompts to rest your gaze on one nearby object.",
        "kind": "steps",
        "duration_seconds": 45,
        "step_seconds": 15,
        "steps": [
            {"cue": "Choose one object in view, or simply rest your gaze."},
            {"cue": "Notice one color or shape."},
            {"cue": "Notice an edge, light, or shadow; nothing needs to be named."},
        ],
        "script_version": "1.0",
    },
    SOUND_NOTICING_ID: {
        "id": SOUND_NOTICING_ID,
        "name": "Sound noticing",
        "short_name": "Listen to nearby sounds",
        "begin_label": "Begin sound noticing",
        "description": "Three gentle 15-second prompts; quiet is fine, and no sound needs to be identified.",
        "kind": "steps",
        "duration_seconds": 45,
        "step_seconds": 15,
        "steps": [
            {"cue": "Notice a sound that is nearby, if there is one."},
            {"cue": "Notice a sound that seems farther away, or enjoy a moment of quiet."},
            {"cue": "Let sounds come and go; you do not need to identify them."},
        ],
        "script_version": "1.0",
    },
    CONTACT_POINTS_ID: {
        "id": CONTACT_POINTS_ID,
        "name": "Support points",
        "short_name": "Notice what supports you",
        "begin_label": "Begin support points",
        "description": "Three gentle 15-second prompts to notice a point of support; there is nothing to change.",
        "kind": "steps",
        "duration_seconds": 45,
        "step_seconds": 15,
        "steps": [
            {"cue": "Notice where you feel supported by the chair or floor."},
            {"cue": "If comfortable, notice your feet or hands resting; you can choose just one point."},
            {"cue": "Let that support be there; nothing needs to change."},
        ],
        "script_version": "1.0",
    },
}

EXERCISE_IDS = tuple(EXERCISES)
STEP_COUNT_LIMIT = max(
    len(exercise.get("steps", [])) for exercise in EXERCISES.values()
)
CYCLE_COUNT_LIMIT = max(exercise.get("cycle_count", 0) for exercise in EXERCISES.values())


def exercise_summary(exercise_id: str | None) -> dict[str, Any] | None:
    if exercise_id not in EXERCISES:
        return None
    return {**EXERCISES[exercise_id], "steps": list(EXERCISES[exercise_id].get("steps", []))}
