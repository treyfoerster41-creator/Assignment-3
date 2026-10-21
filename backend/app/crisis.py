"""Small, explicit phrase routing. This is not a distress detector."""

import re


_PHRASES = (
    "kill myself",
    "end my life",
    "want to die",
    "suicide",
    "self harm",
    "self-harm",
    "hurt myself",
    "harm myself",
    "can't stay safe",
    "cannot stay safe",
)


def contains_limited_crisis_phrase(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    return any(phrase in normalized for phrase in _PHRASES)
