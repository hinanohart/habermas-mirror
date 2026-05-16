import { useState, type FormEvent } from "react";
import * as api from "./api";
import type { SessionOut } from "./types";

export function App() {
  const [session, setSession] = useState<SessionOut | null>(null);
  const [topic, setTopic] = useState("");
  const [author, setAuthor] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reload(): Promise<void> {
    if (!session) return;
    try {
      const s = await api.getSession(session.id);
      setSession(s);
    } catch (e) {
      setError(String(e));
    }
  }

  async function onCreateSession(e: FormEvent): Promise<void> {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await api.createSession(topic.trim());
      setSession(s);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onAddOpinion(e: FormEvent): Promise<void> {
    e.preventDefault();
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      await api.submitOpinion(session.id, author.trim(), body.trim());
      setAuthor("");
      setBody("");
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onFacilitate(): Promise<void> {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      await api.facilitate(session.id);
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!session) {
    return (
      <main className="container">
        <header>
          <h1>habermas-mirror</h1>
          <p className="tagline">
            Self-hostable reference re-implementation of the prompted
            Habermas Machine deliberation facilitator.
          </p>
        </header>
        <form onSubmit={onCreateSession}>
          <label>
            Topic for the deliberation:
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              maxLength={512}
              required
              placeholder="should we adopt remote work?"
            />
          </label>
          <button type="submit" disabled={busy || topic.trim().length === 0}>
            {busy ? "Creating…" : "Create session"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        <Footer />
      </main>
    );
  }

  return (
    <main className="container">
      <header>
        <h1>habermas-mirror</h1>
        <h2>{session.topic}</h2>
        <p className="muted">Session {session.id.slice(0, 8)}…</p>
      </header>

      <section>
        <h3>Participants ({session.opinions.length})</h3>
        {session.opinions.length === 0 && (
          <p className="muted">No opinions yet. Add the first one below.</p>
        )}
        <ul className="opinions">
          {session.opinions.map((o) => (
            <li key={o.id}>
              <strong>{o.author}:</strong> {o.body}
            </li>
          ))}
        </ul>

        <form onSubmit={onAddOpinion}>
          <input
            type="text"
            placeholder="your name"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            maxLength={128}
            required
          />
          <textarea
            placeholder="your opinion"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={4000}
            rows={3}
            required
          />
          <button type="submit" disabled={busy}>
            {busy ? "Submitting…" : "Add opinion"}
          </button>
        </form>
      </section>

      <section>
        <h3>Facilitator</h3>
        <p className="muted">
          Runs three sequential LLM calls (draft → critique → refine). With
          no provider key configured server-side, the mock fallback returns
          deterministic placeholders so you can exercise the UI without
          spending tokens.
        </p>
        <button
          onClick={onFacilitate}
          disabled={busy || session.opinions.length === 0}
        >
          {busy ? "Running…" : "Run facilitator"}
        </button>
      </section>

      <section>
        <h3>Statements ({session.statements.length})</h3>
        {session.statements.length === 0 && (
          <p className="muted">
            No statements yet. Run the facilitator above to draft and revise a
            group statement.
          </p>
        )}
        {session.statements.map((s) => (
          <article key={s.id} className={`statement stage-${s.stage}`}>
            <h4>{s.stage}</h4>
            <p className="muted">provider: {s.provider}</p>
            <pre>{s.body}</pre>
          </article>
        ))}
      </section>

      {error && <p className="error">{error}</p>}
      <Footer />
    </main>
  );
}

function Footer() {
  return (
    <footer>
      <p className="muted">
        Re-implementation of{" "}
        <a href="https://github.com/google-deepmind/habermas_machine">
          DeepMind&rsquo;s prompted reference
        </a>{" "}
        · Apache 2.0 · Not affiliated with Google DeepMind.
      </p>
    </footer>
  );
}
