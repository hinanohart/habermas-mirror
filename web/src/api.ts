import type {
  FacilitateOut,
  OpinionOut,
  SessionOut,
} from "./types";

const BASE = "/api";

async function asJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const body = await r.json();
      if (body?.detail) detail = `${detail}: ${body.detail}`;
    } catch {
      // ignore — non-JSON error body
    }
    throw new Error(detail);
  }
  return r.json();
}

export function createSession(topic: string): Promise<SessionOut> {
  return fetch(`${BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  }).then((r) => asJson<SessionOut>(r));
}

export function submitOpinion(
  sessionId: string,
  author: string,
  body: string,
): Promise<OpinionOut> {
  return fetch(`${BASE}/sessions/${sessionId}/opinions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author, body }),
  }).then((r) => asJson<OpinionOut>(r));
}

export function getSession(sessionId: string): Promise<SessionOut> {
  return fetch(`${BASE}/sessions/${sessionId}`).then((r) =>
    asJson<SessionOut>(r),
  );
}

export function facilitate(sessionId: string): Promise<FacilitateOut> {
  return fetch(`${BASE}/sessions/${sessionId}/facilitate`, {
    method: "POST",
  }).then((r) => asJson<FacilitateOut>(r));
}
