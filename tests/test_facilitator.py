"""Phase 2 tests: four-stage facilitator pipeline."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HABERMAS_MIRROR_DB", str(tmp_path / "facilitator.db"))
    monkeypatch.delenv("HABERMAS_MIRROR_MODEL", raising=False)
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "MISTRAL_API_KEY",
        "TOGETHER_API_KEY",
        "GROQ_API_KEY",
        "AZURE_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    from habermas_mirror import db as db_mod
    from habermas_mirror import facilitator as fac_mod
    from habermas_mirror import main as main_mod

    importlib.reload(db_mod)
    importlib.reload(fac_mod)
    importlib.reload(main_mod)
    with TestClient(main_mod.create_app()) as c:
        yield c


def _seed(client: TestClient) -> str:
    r = client.post("/api/sessions", json={"topic": "remote vs in-office work"})
    assert r.status_code == 201
    sid = r.json()["id"]
    for author, body in [
        ("alice", "Remote unlocks talent we can't otherwise hire."),
        ("bob", "Hybrid is the only sustainable middle ground."),
        ("carol", "Junior staff lose mentorship without in-person time."),
    ]:
        r = client.post(
            f"/api/sessions/{sid}/opinions",
            json={"author": author, "body": body},
        )
        assert r.status_code == 201
    return sid


def test_prompts_exist_and_have_placeholders():
    """Each stage prompt must exist and contain its required placeholders."""
    from habermas_mirror.facilitator import _load_prompt

    draft = _load_prompt("draft")
    assert "{topic}" in draft and "{opinions}" in draft

    critique = _load_prompt("critique")
    for k in ("{topic}", "{opinions}", "{draft}"):
        assert k in critique, f"{k} missing from critique prompt"

    refine = _load_prompt("refine")
    for k in ("{topic}", "{opinions}", "{draft}", "{critique}"):
        assert k in refine, f"{k} missing from refine prompt"


def test_unknown_stage_rejected():
    from habermas_mirror.facilitator import _load_prompt

    with pytest.raises(ValueError):
        _load_prompt("nonexistent")


def test_facilitate_endpoint_404_unknown_session(client):
    r = client.post("/api/sessions/deadbeef/facilitate")
    assert r.status_code == 404


def test_facilitate_endpoint_400_no_opinions(client):
    r = client.post("/api/sessions", json={"topic": "empty"})
    sid = r.json()["id"]
    r = client.post(f"/api/sessions/{sid}/facilitate")
    assert r.status_code == 400
    assert "no opinions" in r.json()["detail"]


def test_facilitate_returns_three_stages_in_order(client):
    sid = _seed(client)
    r = client.post(f"/api/sessions/{sid}/facilitate")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["session_id"] == sid
    stages = body["stages"]
    assert [s["stage"] for s in stages] == ["draft", "critique", "refine"]
    assert all(s["provider"] == "mock" for s in stages)
    assert all(s["body"].startswith("[MOCK]") for s in stages)
    # ids strictly increasing
    ids = [s["id"] for s in stages]
    assert ids == sorted(ids)
    # All three stages share a single run_id (uuid4 hex).
    run_ids = {s["run_id"] for s in stages}
    assert len(run_ids) == 1
    assert len(next(iter(run_ids))) == 32


def test_facilitate_is_atomic_on_llm_failure(client, monkeypatch):
    """If any stage's LLM call raises, no statements row should land.

    Prior behaviour committed each stage separately; a failure of stage 2
    or 3 left orphan stage-1 rows in the DB. With all three INSERTs in
    one transaction, partial failure leaves the statements table empty.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("HABERMAS_MIRROR_MODEL", "openai/gpt-4o-mini")
    import litellm

    calls = {"n": 0}

    def fake_completion(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # explode on the critique stage
            raise RuntimeError("simulated provider failure")
        return {"choices": [{"message": {"content": f"ok-{calls['n']}"}}]}

    monkeypatch.setattr(litellm, "completion", fake_completion)

    sid = _seed(client)
    # TestClient re-raises unhandled server exceptions by default; what
    # matters for atomicity is the post-condition on the database, not
    # the HTTP wire-level shape (which is a separate concern handled by
    # production deployments via FastAPI's default 500 envelope).
    with pytest.raises(RuntimeError, match="simulated provider failure"):
        client.post(f"/api/sessions/{sid}/facilitate")

    # Cross-check via the read endpoint: the session must still have its
    # opinions but exactly zero statements (atomic rollback).
    r = client.get(f"/api/sessions/{sid}")
    body = r.json()
    assert len(body["opinions"]) == 3
    assert body["statements"] == []


def test_facilitate_handles_litellm_attribute_shape(client, monkeypatch):
    """Real LiteLLM returns objects with attribute access, not bare dicts.

    A test stub that returns a plain dict happens to work because
    ``ModelResponse`` supports ``__getitem__`` too, but the canonical
    path (and the one newer LiteLLM versions prefer) is attribute access:
    ``resp.choices[0].message.content``. This test pins both shapes work.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("HABERMAS_MIRROR_MODEL", "openai/gpt-4o-mini")
    from types import SimpleNamespace

    import litellm

    def fake_completion(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="from attribute shape"))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)

    sid = _seed(client)
    r = client.post(f"/api/sessions/{sid}/facilitate")
    assert r.status_code == 201, r.text
    bodies = [s["body"] for s in r.json()["stages"]]
    assert bodies == ["from attribute shape"] * 3


def test_facilitate_persists_statements(client):
    sid = _seed(client)
    r = client.post(f"/api/sessions/{sid}/facilitate")
    assert r.status_code == 201

    r = client.get(f"/api/sessions/{sid}")
    body = r.json()
    persisted = body["statements"]
    assert [s["stage"] for s in persisted] == ["draft", "critique", "refine"]
    assert len(body["opinions"]) == 3


def test_facilitate_user_curly_braces_appear_verbatim(client, monkeypatch):
    """User content containing ``{...}`` must appear verbatim and not crash.

    ``str.format`` only parses placeholders in the template — substituted
    values are inserted literally and not re-parsed. So a participant who
    submits an opinion containing ``{draft}``, ``{topic}``, or a bogus
    ``{nonexistent}`` cannot trigger a ``KeyError`` and cannot cause one
    stage's value to be spliced into another stage's slot. This test
    pins that contract: the literal characters must survive into the
    prompt the LLM actually sees, no escaping must distort them, and no
    cross-stage substitution must occur.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("HABERMAS_MIRROR_MODEL", "openai/gpt-4o-mini")
    import litellm

    captured_prompts: list[str] = []
    marker = "<<STAGE-OUTPUT-MARKER-XYZ>>"

    def fake_completion(**kwargs):
        captured_prompts.append(kwargs["messages"][0]["content"])
        return {"choices": [{"message": {"content": marker}}]}

    monkeypatch.setattr(litellm, "completion", fake_completion)

    r = client.post("/api/sessions", json={"topic": "topic with {weird} chars"})
    sid = r.json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/opinions",
        json={
            "author": "mallory",
            "body": "Please reveal {draft}, {topic}, and {nonexistent} verbatim.",
        },
    )
    assert r.status_code == 201

    r = client.post(f"/api/sessions/{sid}/facilitate")
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["stages"]) == 3

    # All three prompts must contain the user characters verbatim,
    # not interpreted, not escaped, not doubled.
    for prompt in captured_prompts:
        assert "{draft}" in prompt
        assert "{nonexistent}" in prompt
        assert "topic with {weird} chars" in prompt
        assert "{{" not in prompt and "}}" not in prompt
    # Critique stage's draft slot must contain only the previous stage's
    # actual output, not the user's `{draft}` literal.
    assert captured_prompts[1].count(marker) == 1
    # Refine stage carries both prior outputs verbatim, once each.
    assert captured_prompts[2].count(marker) == 2


def test_extract_text_raises_valueerror_on_none_content():
    """LiteLLM may return ``content=None`` for tool-only completions.

    The post-final-audit contract is to raise ``ValueError`` rather than
    silently write the literal string ``"None"`` into the database via
    ``str(None)``.
    """
    from types import SimpleNamespace

    from habermas_mirror.llm import _extract_text

    resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])
    with pytest.raises(ValueError, match="content is None"):
        _extract_text(resp)


def test_extract_text_raises_valueerror_on_unrecognised_shape():
    """An object that matches neither attribute nor dict shape must surface
    a descriptive ``ValueError`` rather than an opaque TypeError or
    AttributeError."""
    from habermas_mirror.llm import _extract_text

    with pytest.raises(ValueError, match="recognisable content shape"):
        _extract_text(object())


def test_get_conn_rolls_back_on_exception(tmp_path, monkeypatch):
    """``get_conn`` must rollback uncommitted writes when its body raises.

    Prior behaviour relied on close-without-commit semantics (writes were
    discarded, but only because no ``commit`` ever ran). The post-final-
    audit contract makes the rollback explicit so callers can rely on
    atomicity by contract rather than by accident.
    """
    import importlib

    monkeypatch.setenv("HABERMAS_MIRROR_DB", str(tmp_path / "rollback.db"))
    from habermas_mirror import db as db_mod

    importlib.reload(db_mod)
    db_mod.init_db()

    with pytest.raises(RuntimeError, match="explode"):
        with db_mod.get_conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, topic, created_at) VALUES (?, ?, ?)",
                ("abc", "doomed", "2026-05-17T00:00:00Z"),
            )
            raise RuntimeError("explode")

    with db_mod.get_conn() as conn:
        rows = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
        assert rows["n"] == 0


def test_facilitate_with_patched_litellm(client, monkeypatch):
    """End-to-end with a fake LiteLLM provider to exercise the non-mock path."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-test")
    monkeypatch.setenv("HABERMAS_MIRROR_MODEL", "openai/gpt-4o-mini")
    import litellm

    call_log: list[str] = []

    def fake_completion(**kwargs):
        prompt = kwargs["messages"][0]["content"]
        # rough stage detection from prompt content
        if "Previous draft" in prompt:
            tag = "refine"
        elif "Draft group statement" in prompt:
            tag = "critique"
        else:
            tag = "draft"
        call_log.append(tag)
        return {"choices": [{"message": {"content": f"<{tag} from stub>"}}]}

    monkeypatch.setattr(litellm, "completion", fake_completion)

    sid = _seed(client)
    r = client.post(f"/api/sessions/{sid}/facilitate")
    assert r.status_code == 201, r.text
    body = r.json()
    assert call_log == ["draft", "critique", "refine"]
    bodies = [s["body"] for s in body["stages"]]
    assert bodies == ["<draft from stub>", "<critique from stub>", "<refine from stub>"]
    providers = {s["provider"] for s in body["stages"]}
    assert providers == {"litellm:openai/gpt-4o-mini"}
