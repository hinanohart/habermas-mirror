"""LLM provider abstraction.

Uses LiteLLM when an upstream provider API key is present in the process
environment; otherwise returns a deterministic mock string so that the API
and pipeline are fully runnable for development and tests without any secret
being handled by this code.

No provider key is ever read into a Python variable for transport — LiteLLM
reads provider keys directly from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = os.environ.get("HABERMAS_MIRROR_MODEL", "openai/gpt-4o-mini")

_PROVIDER_KEY_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "GROQ_API_KEY",
    "AZURE_API_KEY",
)


@dataclass
class LLMResponse:
    text: str
    provider: str  # "litellm:<model>" or "mock"


def _any_provider_key_set() -> bool:
    return any(os.environ.get(name) for name in _PROVIDER_KEY_ENV_VARS)


def complete(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> LLMResponse:
    """Single-turn completion. Falls back to mock if no provider key is set."""
    if not _any_provider_key_set():
        return LLMResponse(text=_mock_completion(prompt), provider="mock")

    import litellm  # imported lazily so test envs without litellm still work

    chosen = model or DEFAULT_MODEL
    resp = litellm.completion(
        model=chosen,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text = resp["choices"][0]["message"]["content"]
    return LLMResponse(text=text, provider=f"litellm:{chosen}")


def _mock_completion(prompt: str) -> str:
    head = prompt.strip().splitlines()[0][:100] if prompt.strip() else ""
    return (
        "[MOCK] No LLM provider API key detected in the environment "
        "(set OPENAI_API_KEY / ANTHROPIC_API_KEY / etc. to enable real "
        "completions via LiteLLM). "
        f'Prompt opener: "{head}"'
    )
