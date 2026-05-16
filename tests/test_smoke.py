"""Phase 1 smoke tests: API plumbing + DB lifecycle + LLM mock fallback."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HABERMAS_MIRROR_DB", str(tmp_path / "test.db"))
    # ensure db / main re-read env on each test
    from habermas_mirror import db as db_mod
    from habermas_mirror import main as main_mod

    importlib.reload(db_mod)
    importlib.reload(main_mod)
    return TestClient(main_mod.create_app())


def test_healthz_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_session_lifecycle(client):
    r = client.post("/api/sessions", json={"topic": "should we adopt remote work?"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert len(sid) == 32  # uuid4 hex

    for author, body in [
        ("alice", "I support flexibility."),
        ("bob", "I worry about onboarding."),
    ]:
        r = client.post(
            f"/api/sessions/{sid}/opinions",
            json={"author": author, "body": body},
        )
        assert r.status_code == 201, r.text

    r = client.get(f"/api/sessions/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["topic"] == "should we adopt remote work?"
    assert len(body["opinions"]) == 2
    assert {o["author"] for o in body["opinions"]} == {"alice", "bob"}
    assert body["statements"] == []


def test_unknown_session_404(client):
    r = client.get("/api/sessions/deadbeef")
    assert r.status_code == 404
    r = client.post(
        "/api/sessions/deadbeef/opinions",
        json={"author": "x", "body": "y"},
    )
    assert r.status_code == 404


def test_opinion_validation(client):
    r = client.post("/api/sessions", json={"topic": "t"})
    sid = r.json()["id"]
    # empty body rejected
    r = client.post(
        f"/api/sessions/{sid}/opinions",
        json={"author": "alice", "body": ""},
    )
    assert r.status_code == 422
    # oversize body rejected
    r = client.post(
        f"/api/sessions/{sid}/opinions",
        json={"author": "alice", "body": "x" * 5000},
    )
    assert r.status_code == 422


def test_llm_mock_when_no_key(monkeypatch):
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
    monkeypatch.delenv("HABERMAS_MIRROR_MODEL", raising=False)
    from habermas_mirror.llm import complete

    resp = complete("hello world\nsecond line")
    assert resp.provider == "mock"
    assert "[MOCK]" in resp.text
    # mock must NOT echo prompt content (PII / secret leakage prevention)
    assert "hello world" not in resp.text
    assert "second line" not in resp.text
    # determinism: same prompt → same response
    resp2 = complete("hello world\nsecond line")
    assert resp.text == resp2.text
    # different prompt → different fingerprint
    resp3 = complete("different prompt")
    assert resp3.text != resp.text


def test_llm_mock_when_model_unset(monkeypatch):
    # provider key is present, but no model chosen → must still mock
    monkeypatch.setenv("OPENAI_API_KEY", "sk-do-not-use-mock-anyway")
    monkeypatch.delenv("HABERMAS_MIRROR_MODEL", raising=False)
    from habermas_mirror.llm import complete

    resp = complete("any prompt")
    assert resp.provider == "mock"


def test_llm_uses_litellm_when_configured(monkeypatch):
    """Real LiteLLM codepath is reached when both model + key are set.

    We patch `litellm.completion` so the test never makes a network call and
    never depends on a real API key being valid — but we do exercise the
    branch in `complete()` that calls it.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-test")
    monkeypatch.setenv("HABERMAS_MIRROR_MODEL", "openai/gpt-4o-mini")

    import litellm

    def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "stubbed reply"}}]}

    monkeypatch.setattr(litellm, "completion", fake_completion)

    from habermas_mirror.llm import complete

    resp = complete("anything")
    assert resp.provider == "litellm:openai/gpt-4o-mini"
    assert resp.text == "stubbed reply"
