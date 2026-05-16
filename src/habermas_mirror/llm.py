"""LLM provider abstraction.

Uses LiteLLM when the caller has explicitly chosen a model (via the
`HABERMAS_MIRROR_MODEL` environment variable or the `model=` argument) AND a
matching provider key is present in the environment. Otherwise returns a
deterministic mock so the API and pipeline are fully runnable for development
and tests without any secret being handled by this code.

There is intentionally no built-in default model: picking one would
preferentially promote one vendor over others, undermining the project's
provider-agnostic stance. Set `HABERMAS_MIRROR_MODEL` (e.g. `openai/gpt-4o-mini`,
`anthropic/claude-3-5-sonnet`, `gemini/gemini-1.5-pro`, ...) to enable real
completions.

No provider key value is ever read into a Python variable for transport —
LiteLLM reads provider keys directly from the environment.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


def _configured_model() -> str | None:
    """Return the operator-chosen model, or None if unset/blank."""
    val = os.environ.get("HABERMAS_MIRROR_MODEL", "").strip()
    return val or None


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
    """Single-turn completion.

    Falls back to the deterministic mock when either (a) no model has been
    explicitly chosen, or (b) no provider key is present. Never picks a
    default model on the caller's behalf.
    """
    chosen = model or _configured_model()
    if not chosen or not _any_provider_key_set():
        return LLMResponse(text=_mock_completion(prompt), provider="mock")

    import litellm  # lazy import so test envs without litellm still work

    resp = litellm.completion(
        model=chosen,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text = _extract_text(resp)
    return LLMResponse(text=text, provider=f"litellm:{chosen}")


def _extract_text(resp: object) -> str:
    """Extract the assistant content from a LiteLLM completion response.

    LiteLLM exposes its ``ModelResponse`` with both attribute access
    (``resp.choices[0].message.content``) and dict-like ``__getitem__``.
    Older provider shims and some test stubs return plain dicts; newer
    LiteLLM versions return Pydantic models where attribute access is
    the canonical path. Try attribute access first and fall back to
    subscripting so we work against both shapes without depending on
    the exact LiteLLM version pinned in the venv.
    """
    try:
        choice = resp.choices[0]  # type: ignore[attr-defined]
        message = choice.message
        content = message.content
        if content is None:
            raise AttributeError
        return str(content)
    except (AttributeError, IndexError, TypeError):
        pass
    return str(resp["choices"][0]["message"]["content"])  # type: ignore[index]


def _mock_completion(prompt: str) -> str:
    """Deterministic placeholder.

    Returns a non-leaky string. We attach a short SHA-256 fingerprint of the
    prompt so tests can assert determinism (same prompt → same response)
    without ever echoing user-supplied content back into the response body
    or — via the API layer — into the SQLite ``statements`` table.
    """
    fp = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
    return (
        "[MOCK] No LLM provider configured. Set HABERMAS_MIRROR_MODEL (for "
        "example openai/gpt-4o-mini, anthropic/claude-3-5-sonnet, "
        "gemini/gemini-1.5-pro) and the matching provider API key to enable "
        f"real completions via LiteLLM. (prompt-fingerprint sha256:{fp})"
    )
