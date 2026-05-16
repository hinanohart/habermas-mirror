"""Four-stage facilitator pipeline.

Pipeline (matching the prompted reference in Tessler et al., Science 2024):

    gather opinions  →  draft  →  critique  →  refine

The "gather" step is implicit: it reads the opinions that participants
have already submitted via the API. The remaining three stages each
call the LLM once. All three persistence writes happen in a single
transaction at the very end, tagged with a shared ``run_id`` (uuid4)
so the three rows can be correlated, ordered, and rolled back together.
If any LLM call fails mid-pipeline, nothing is written; the alternative
(per-stage autocommit) used to leave orphan ``draft`` rows behind when
``critique`` or ``refine`` raised.

This is a single-provider implementation: by default all three LLM
calls go to the same model. The structural implications of that choice
are documented in ``docs/BFT_NOTE.md`` — single-provider operation is
equivalent to a single-owner attestation and should not be marketed as
a consensus mechanism.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from habermas_mirror.db import get_conn
from habermas_mirror.llm import LLMResponse, complete
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


def _insert_statement(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    stage: str,
    response: LLMResponse,
    run_id: str,
    now_iso: str,
) -> StatementOut:
    cur = conn.execute(
        "INSERT INTO statements "
        "(session_id, stage, body, provider, run_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, stage, response.text, response.provider, run_id, now_iso),
    )
    oid = cur.lastrowid
    if oid is None:
        # sqlite3 is documented to return an int after a single-row INSERT;
        # the None branch is a driver-inconsistency guard rather than a
        # path we expect to hit.
        raise RuntimeError("sqlite INSERT did not return a lastrowid")
    return StatementOut(
        id=oid,
        session_id=session_id,
        stage=stage,
        body=response.text,
        provider=response.provider,
        run_id=run_id,
        created_at=datetime.fromisoformat(now_iso),
    )


def facilitate(session_id: str) -> list[StatementOut]:
    """Run the three-LLM-call pipeline (draft → critique → refine).

    The implicit ``gather`` stage reads opinions from the DB. If there
    are zero opinions, ``ValueError`` is raised. If the session itself
    is unknown, ``LookupError`` is raised.

    All three LLM calls are made BEFORE any DB write so that a slow or
    failing LLM does not hold a SQLite write lock for the duration. The
    three resulting rows are then inserted in a single transaction with
    a shared ``run_id`` so partial-failure half-runs cannot leak into
    the ``statements`` table.

    Returns the three persisted statements in order.
    """
    topic, opinions = _gather_opinions(session_id)
    if not opinions:
        raise ValueError("cannot facilitate a session with no opinions")
    opinions_block = _format_opinions(opinions)

    draft_prompt = _load_prompt("draft").format(topic=topic, opinions=opinions_block)
    draft = complete(draft_prompt)

    critique_prompt = _load_prompt("critique").format(
        topic=topic, opinions=opinions_block, draft=draft.text
    )
    critique = complete(critique_prompt)

    refine_prompt = _load_prompt("refine").format(
        topic=topic,
        opinions=opinions_block,
        draft=draft.text,
        critique=critique.text,
    )
    refine = complete(refine_prompt)

    run_id = uuid4().hex
    now = _now_iso()
    stages = (("draft", draft), ("critique", critique), ("refine", refine))
    with get_conn() as conn:
        return [
            _insert_statement(
                conn,
                session_id=session_id,
                stage=stage,
                response=response,
                run_id=run_id,
                now_iso=now,
            )
            for stage, response in stages
        ]
