"""Four-stage facilitator pipeline.

Pipeline (matching the prompted reference in Tessler et al., Science 2024):

    gather opinions  →  draft  →  critique  →  refine

The "gather" step is implicit: it reads the opinions that participants
have already submitted via the API. The remaining three stages each
call the LLM once and persist their output to the ``statements`` table
so the full transcript is available for inspection and audit.

This is a single-provider implementation: by default all three LLM
calls go to the same model. The structural implications of that choice
are documented in ``docs/BFT_NOTE.md`` — single-provider operation is
equivalent to a single-owner attestation and should not be marketed as
a consensus mechanism.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from habermas_mirror.db import get_conn
from habermas_mirror.llm import complete
from habermas_mirror.models import StatementOut

STAGES = ("draft", "critique", "refine")

_PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_prompt(stage: str) -> str:
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage!r}")
    return (_PROMPT_DIR / f"{stage}.md").read_text(encoding="utf-8")


def _gather_opinions(session_id: str) -> tuple[str, list[tuple[str, str]]]:
    """Return ``(topic, [(author, body), ...])`` for a session.

    Raises ``LookupError`` if the session does not exist.
    """
    with get_conn() as conn:
        s = conn.execute(
            "SELECT topic FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if s is None:
            raise LookupError(f"session {session_id!r} not found")
        rows = conn.execute(
            "SELECT author, body FROM opinions WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return s["topic"], [(r["author"], r["body"]) for r in rows]


def _format_opinions(opinions: list[tuple[str, str]]) -> str:
    # ``str.format`` only parses placeholders in the template string and
    # never re-parses substituted values — verified against Python
    # semantics — so curly braces inside opinion bodies appear verbatim
    # in the final prompt and cannot cross-substitute another stage's
    # value. No escaping is needed or wanted here; escaping would alter
    # what the model actually reads.
    return "\n\n".join(
        f"Participant {i + 1} ({author}):\n{body}" for i, (author, body) in enumerate(opinions)
    )


def _record(session_id: str, stage: str, body: str, provider: str) -> StatementOut:
    now = _now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO statements "
            "(session_id, stage, body, provider, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, stage, body, provider, now),
        )
        sid_row = cur.lastrowid
    return StatementOut(
        id=sid_row,
        session_id=session_id,
        stage=stage,
        body=body,
        provider=provider,
        created_at=datetime.fromisoformat(now),
    )


def facilitate(session_id: str) -> list[StatementOut]:
    """Run the three-LLM-call pipeline (draft → critique → refine).

    The implicit ``gather`` stage reads opinions from the DB. If there
    are zero opinions, ``ValueError`` is raised. If the session itself
    is unknown, ``LookupError`` is raised.

    Returns the three persisted statements in order.
    """
    topic, opinions = _gather_opinions(session_id)
    if not opinions:
        raise ValueError("cannot facilitate a session with no opinions")
    opinions_block = _format_opinions(opinions)

    results: list[StatementOut] = []

    draft_prompt = _load_prompt("draft").format(topic=topic, opinions=opinions_block)
    draft = complete(draft_prompt)
    results.append(_record(session_id, "draft", draft.text, draft.provider))

    critique_prompt = _load_prompt("critique").format(
        topic=topic, opinions=opinions_block, draft=draft.text
    )
    critique = complete(critique_prompt)
    results.append(_record(session_id, "critique", critique.text, critique.provider))

    refine_prompt = _load_prompt("refine").format(
        topic=topic,
        opinions=opinions_block,
        draft=draft.text,
        critique=critique.text,
    )
    refine = complete(refine_prompt)
    results.append(_record(session_id, "refine", refine.text, refine.provider))

    return results
