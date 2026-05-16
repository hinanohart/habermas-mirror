# Changelog

All notable changes to `habermas-mirror` are recorded in this file. The
format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it ships a 0.1.0 tag.

## [Unreleased]

Pre-tag development under version 0.0.1. The history below is grouped
by build phase rather than by date because none of these commits have
shipped yet.

### Phase 0 — repo skeleton

- Apache 2.0 LICENSE (full text, unmodified) and matching NOTICE with
  upstream attribution to Tessler et al. (*Science*, 2024) and an
  explicit non-affiliation disclaimer for Google DeepMind.
- README skeleton: *Why this exists* / *Non-goals* / *Acknowledgment* /
  *Roadmap* / *Sunset condition* / *Citation*.
- `pyproject.toml` (hatchling, Python ≥ 3.12).
- `.gitignore` covering Python build artefacts, virtual environments,
  secrets (`.env`, `*.pem`, `*.key`), SQLite files, Node, and editor
  lockfiles.
- Commit author normalised to *habermas-mirror contributors* so the
  initial commit does not attribute the project to Claude or Anthropic.

### Phase 1 — FastAPI + LiteLLM + SQLite

- `src/habermas_mirror/db.py`: stdlib `sqlite3` schema with `sessions`,
  `opinions`, and `statements` tables (foreign keys on, indexes on
  `session_id`).
- `src/habermas_mirror/models.py`: Pydantic v2 request/response models.
- `src/habermas_mirror/llm.py`: LiteLLM wrapper that requires an
  explicitly chosen model (no built-in default to avoid promoting one
  vendor). Falls back to a deterministic SHA-256-fingerprint mock when
  no model or provider key is configured. No provider key value is
  ever held in a Python variable for transport.
- `src/habermas_mirror/api/opinions.py`: `POST /api/sessions`,
  `POST /api/sessions/{id}/opinions`, `GET /api/sessions/{id}`.
- `src/habermas_mirror/main.py`: FastAPI app factory + `/healthz`.
  `init_db` runs inside the FastAPI lifespan so importing the module
  has no SQLite side effect.
- `habermas-mirror` console script (`serve`, `version`).
- 7 smoke tests covering the lifecycle, 404 / 422 error paths, the
  mock-only LLM path, and a `monkeypatch.setattr(litellm, "completion", ...)`
  path that exercises the real LiteLLM branch without a network call.

### Phase 2 — four-stage facilitator pipeline

- `src/habermas_mirror/facilitator.py`: orchestrates the three LLM
  stages (draft → critique → refine), reads opinions from the DB for
  the implicit gather step, and persists each stage to `statements`.
- `src/habermas_mirror/prompts/{draft,critique,refine}.md`: prompt
  templates with `str.format` placeholders. Documented contract: user
  content with `{...}` characters appears verbatim and never
  cross-substitutes another stage's value (Python `str.format` does not
  re-parse substituted values; this is pinned by a regression test).
- `src/habermas_mirror/api/facilitate.py`: `POST /api/sessions/{id}/facilitate`
  with 404 on unknown session and 400 on no-opinions.
- `docs/BFT_NOTE.md`: honest single-provider-operation note —
  structurally equivalent to a single-party attestation, not a
  consensus mechanism.
- 7 additional tests covering prompt loading, endpoint error paths,
  three-stage ordering under both mock and patched-LiteLLM paths,
  persistence, and the curly-brace pass-through contract.

### Phase 3 — minimal React (Vite) UI + dev-restricted CORS

- `web/`: Vite 5 + React 18 + TypeScript 5.5 single-component UI. Strict
  TypeScript with `noUnusedLocals` / `noUnusedParameters`. Single
  `App.tsx`; no router, no UI framework, no state library.
- Backend `CORSMiddleware`: dev origins (`localhost:5173`,
  `127.0.0.1:5173`) only; `allow_credentials=False`; methods restricted
  to GET/POST/OPTIONS.
- 2 backend CORS tests (allow / reject) + 4 release-invariant tests
  that pin the README roadmap, `docs/BFT_NOTE.md` link, the DeepMind
  non-affiliation disclaimer, and the sunset clause.

### Phase 4 — docs, smoke, release artefact

- README Usage section with explicit two-shell setup (uvicorn +
  `vite dev`) and the env-var-based provider configuration.
- `CONTRIBUTING.md` with scope discipline, local-dev recipe, what we
  will not accept, and the sunset clause.
- `CHANGELOG.md` (this file).
- `RELEASE_NOTES.md` draft for the eventual 0.0.1 → 0.1.0 tag.
- Optional production serve path: when `web/dist/` is present, the
  FastAPI app mounts it as `StaticFiles` so a single `habermas-mirror serve`
  process can serve both API and UI. `HABERMAS_MIRROR_WEB_DIST` env var
  lets operators point at a bundle outside the source tree.
- `pyproject.toml`: project URLs added; classifier moved from
  *Planning* to *Alpha*.
