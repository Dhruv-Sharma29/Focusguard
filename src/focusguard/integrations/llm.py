"""LLM integration for FocusGuard AI coach.

Supports two backends:
  - Ollama (default): fully local, free, no data leaves the machine
  - OpenAI (opt-in): requires API key stored via keyring

CRITICAL PRIVACY RULE: Only minimal context is ever sent to the LLM:
  - Current goal description
  - How long the user has been stuck
  - Last 3 app names (no window titles, no URLs)
  - Current focus score (a single number)

NEVER sent: full activity history, window titles, browsing history,
file contents, git diffs, or any PII.
"""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console

from focusguard.config import load_config
from focusguard.security.keyring_store import get_secret

logger = logging.getLogger(__name__)
console = Console(stderr=True)


class LLMError(Exception):
    """Raised when LLM communication fails."""


def chat(
    system_prompt: str,
    user_message: str,
    provider: str | None = None,
) -> str:
    """Send a message to the LLM and return the response.

    Args:
        system_prompt: The system prompt defining personality/behavior.
        user_message: The user's message with minimal context.
        provider: Override the provider ('ollama' or 'openai').

    Returns:
        The LLM's response text.

    Raises:
        LLMError: If the LLM is unavailable or returns an error.
    """
    config = load_config()
    provider = provider or config.ai.provider

    if provider == "ollama":
        return _chat_ollama(system_prompt, user_message, config.ai.ollama_model)
    elif provider == "openai":
        return _chat_openai(system_prompt, user_message, config.ai.openai_model)
    else:
        raise LLMError(f"Unknown AI provider: {provider}")


def _chat_ollama(system_prompt: str, user_message: str, model: str) -> str:
    """Send a message via Ollama (local LLM)."""
    try:
        import ollama as ollama_client  # type: ignore[import-untyped]
    except ImportError:
        raise LLMError(
            "Ollama Python package not installed. "
            "Install with: pip install focusguard[ai]"
        )

    try:
        response = ollama_client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response["message"]["content"]  # type: ignore[index]
    except Exception as e:
        if "connection" in str(e).lower():
            raise LLMError(
                "Cannot connect to Ollama. Is it running? "
                "Start with: ollama serve"
            )
        raise LLMError(f"Ollama error: {e}")


def _chat_openai(system_prompt: str, user_message: str, model: str) -> str:
    """Send a message via OpenAI API."""
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError:
        raise LLMError(
            "OpenAI Python package not installed. "
            "Install with: pip install focusguard[ai]"
        )

    api_key = get_secret("openai_api_key")
    if not api_key:
        raise LLMError(
            "OpenAI API key not configured. "
            "Set it with: focusguard coach setup-openai"
        )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise LLMError(f"OpenAI error: {e}")


def is_available(provider: str | None = None) -> bool:
    """Check if the LLM backend is available.

    Returns:
        True if the provider is installed and reachable.
    """
    config = load_config()
    provider = provider or config.ai.provider

    if provider == "ollama":
        try:
            import ollama as ollama_client  # type: ignore[import-untyped]
            ollama_client.list()
            return True
        except Exception:
            return False
    elif provider == "openai":
        try:
            import openai  # type: ignore[import-untyped]
            return get_secret("openai_api_key") is not None
        except ImportError:
            return False

    return False
