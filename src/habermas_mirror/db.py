"""SQLite persistence layer.

stdlib sqlite3 only — no ORM. Schema is small and migrations are out of scope
for the reference implementation; reset the DB file to upgrade.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _db_path() -> Path:
    return Path(os.environ.get("HABERMAS_MIRROR_DB", "habermas-mirror.db"))


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    topic      TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opinions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    author     TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS statements (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    stage      TEXT NOT NULL,
    body       TEXT NOT NULL,
    provider   TEXT NOT NULL,
    run_id     TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_opinions_session    ON opinions (session_id);
CREATE INDEX IF NOT EXISTS idx_statements_session  ON statements (session_id);
CREATE INDEX IF NOT EXISTS idx_statements_run      ON statements (run_id);
"""


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    """Apply the SQLite pragmas this project relies on.

    - foreign_keys: schema integrity (e.g. opinions cannot orphan their session).
    - journal_mode=WAL: lets readers and writers proceed concurrently, which
      matters as soon as an opinion-write and a facilitate-write race.
    - busy_timeout=5000: gives a brief wait window instead of surfacing
      ``database is locked`` to the API caller under contention.
    """
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")


def init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        _apply_pragmas(conn)
        conn.executescript(SCHEMA)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Connection context manager with explicit commit/rollback contract.

    On normal exit the open transaction is committed. On exception the
    transaction is explicitly rolled back before the exception is re-raised,
    so callers (e.g. ``facilitator.facilitate``) can rely on atomicity by
    contract rather than by accident of ``close()`` discarding uncommitted
    writes.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()
