"""Shared helper for calling the OpenAI Chat Completions API with a JSON
response format, used by every agent. Returns None on any failure so
callers can fall back to deterministic logic.
"""
import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("foodflow.agents")

_client = None


def _get_client():
    global _client
    if _client is None and settings.ai_enabled:
        try:
            from openai import OpenAI

            _client = OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to initialize OpenAI client: %s", e)
            _client = None
    return _client


def call_json_agent(system_prompt: str, user_prompt: str) -> Optional[dict]:
    """Calls the configured OpenAI model requesting a JSON object response.
    Returns the parsed dict, or None if AI is disabled or the call fails."""
    if not settings.ai_enabled:
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            timeout=20,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:  # noqa: BLE001 - any AI/network failure triggers fallback
        logger.warning("AI agent call failed, using fallback: %s", e)
        return None
