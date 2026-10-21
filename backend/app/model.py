from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx


MOCK_REPLY = (
    "This is a saved demo response, not a live model reply. You can try the fixed "
    "4-in/6-out breathing practice, pause, or leave this prototype."
)
MODEL_FALLBACK_REPLY = (
    "The live model is unavailable right now. You can still try the fixed "
    "4-in/6-out breathing practice, pause, or leave this prototype."
)
SYSTEM_INSTRUCTION = """You are a constrained conversational component in Still, a local coursework skills prototype evaluated only with fictional scenarios. Reply in one or two short, neutral, non-clinical sentences. Acknowledge only what the user explicitly wrote. You may mention that the user can choose the fixed 4-in/6-out breathing practice, pause, or leave. Never diagnose, infer a mental state, claim effectiveness, provide therapy or other advice, invent or modify exercise steps, or imply a person is monitoring the user. Do not give crisis guidance; the application has a separate fixed resource panel. Keep the reply under 240 characters."""


def load_project_env() -> None:
    """Read simple KEY=value entries without printing or logging their values."""
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if not env_path.is_file():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#") or "=" not in candidate:
            continue
        name, value = candidate.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"'")
        if name and name.replace("_", "").isalnum():
            os.environ.setdefault(name, value)


def model_configuration() -> tuple[str | None, str]:
    load_project_env()
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        model = "gemini-3.8-flash"
    return key, model


async def request_gemini_reply(message: str, history: list[dict[str, str]]) -> str:
    api_key, model = model_configuration()
    if not api_key:
        raise RuntimeError("live model is not configured")

    contents: list[dict[str, Any]] = []
    for item in history[-6:]:
        role = "model" if item["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": item["text"][:500]}]})
    contents.append({"role": "user", "parts": [{"text": message[:500]}]})
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 100, "temperature": 0.4},
    }
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    timeout = httpx.Timeout(12.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            endpoint,
            headers={"x-goog-api-key": api_key},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = " ".join(
        part.get("text", "").strip()
        for part in parts
        if isinstance(part.get("text"), str) and part.get("text", "").strip()
    )
    if not text:
        raise ValueError("model returned no text")
    return text[:500]


async def generate_reply(message: str, history: list[dict[str, str]]) -> tuple[str, str]:
    api_key, _model = model_configuration()
    if not api_key:
        return MOCK_REPLY, "mock"
    try:
        return await request_gemini_reply(message, history), "gemini"
    except Exception:
        # Provider details and request headers may contain sensitive data. Keep this sanitized.
        return MODEL_FALLBACK_REPLY, "fallback"
