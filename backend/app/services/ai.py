"""AI fortune generation with automatic fallback.

Contract:
    generate_fortune() -> (message: str, source: "ai" | "seed")

    Never raises. If the LLM call fails for ANY reason — missing API key,
    network error, rate limit, timeout, bad response — we log a one-line
    warning and return a random seed message with source="seed".
    The endpoint handler doesn't need to know about any of this.

Why the fallback pattern:
    - The app must stay usable even when you clone it with no API key.
    - Prod should degrade gracefully if OpenAI has an incident.
    - Keeps the HTTP layer simple: one call, always a result.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SEED_EPOCH_CUTOFF, SOURCE_AI, SOURCE_SEED, Fortune

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You write fortune cookie messages. "
    "Output ONLY the message itself, one line, under 120 characters. "
    "Be encouraging, a bit wise, occasionally playful. "
    "No quotes, no emoji, no preface, no trailing period required."
)

USER_PROMPT = "Give me one fresh fortune cookie message."


def _pick_seed_message(db: Session) -> str:
    """Return a random seed message, or a hardcoded last-resort string.

    We keep a hardcoded fallback so the app never returns a 500 even
    if the DB hasn't been seeded yet — useful on a freshly provisioned box.
    """
    stmt = (
        select(Fortune)
        .where(Fortune.created_at < SEED_EPOCH_CUTOFF)
        .order_by(func.random())
        .limit(1)
    )
    seed = db.execute(stmt).scalar_one_or_none()
    if seed is not None:
        return seed.message
    return "Fortune favors the person who reads the docs."


def _call_openai() -> str | None:
    """Call the OpenAI chat completion API. Return the text, or None on any failure."""
    if not settings.ai_enabled:
        return None

    # Import lazily so the app still boots when the openai package isn't installed
    # (e.g. a minimal test environment).
    try:
        from openai import OpenAI
    except ImportError:  # pragma: no cover
        logger.warning("openai package not installed; falling back to seed")
        return None

    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=0,  # we fall back immediately, no silent slow retries
        )
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            max_tokens=60,
            temperature=1.0,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return None
        # Trim stray quotes or markdown the model sometimes adds.
        text = text.strip('"').strip("'").strip()
        return text[:280]
    except Exception as exc:  # broad on purpose — we always want to fall back
        logger.warning("OpenAI call failed, falling back to seed: %s", exc)
        return None


def generate_fortune(db: Session) -> tuple[str, str]:
    """Return (message, source). `source` is one of 'ai' or 'seed'."""
    ai_text = _call_openai()
    if ai_text:
        return ai_text, SOURCE_AI
    return _pick_seed_message(db), SOURCE_SEED


# Re-export the source constants for the router's convenience.
__all__ = ["generate_fortune", "SOURCE_AI", "SOURCE_SEED"]
