"""Session + opinion HTTP endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from habermas_mirror.db import get_conn
from habermas_mirror.models import (
    OpinionIn,
    OpinionOut,
    SessionIn,
    SessionOut,
    StatementOut,
)

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionIn) -> SessionOut:
    sid = uuid4().hex
    now = _now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, topic, created_at) VALUES (?, ?, ?)",
            (sid, payload.topic, now),
        )
    return SessionOut(
        id=sid,
        topic=payload.topic,
        created_at=datetime.fromisoformat(now),
        opinions=[],
        statements=[],
    )


@router.post(
    "/sessions/{session_id}/opinions",
    response_model=OpinionOut,
    status_code=201,
)
def submit_opinion(session_id: str, payload: OpinionIn) -> OpinionOut:
    now = _now_iso()
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="session not found")
        cur = conn.execute(
            "INSERT INTO opinions (session_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (session_id, payload.author, payload.body, now),
        )
        oid = cur.lastrowid
        if oid is None:
            raise RuntimeError("sqlite INSERT did not return a lastrowid")
    return OpinionOut(
        id=oid,
        session_id=session_id,
        author=payload.author,
        body=payload.body,
        created_at=datetime.fromisoformat(now),
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str) -> SessionOut:
    with get_conn() as conn:
        s = conn.execute(
            "SELECT id, topic, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        opinion_rows = conn.execute(
            "SELECT id, session_id, author, body, created_at "
            "FROM opinions WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        statement_rows = conn.execute(
            "SELECT id, session_id, stage, body, provider, run_id, created_at "
            "FROM statements WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

    opinions = [
        OpinionOut(
            id=r["id"],
            session_id=r["session_id"],
            author=r["author"],
            body=r["body"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in opinion_rows
    ]
    statements = [
        StatementOut(
            id=r["id"],
            session_id=r["session_id"],
            stage=r["stage"],
            body=r["body"],
            provider=r["provider"],
            run_id=r["run_id"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in statement_rows
    ]
    return SessionOut(
        id=s["id"],
        topic=s["topic"],
        created_at=datetime.fromisoformat(s["created_at"]),
        opinions=opinions,
        statements=statements,
    )
