# Contributing to habermas-mirror

`habermas-mirror` is a deliberately small reference implementation. The
goal of this guide is to make it easy to land *small, honest* changes
without accumulating scope.

## Scope, in one paragraph

This repository re-implements the prompted four-stage pipeline described
in Tessler et al., *Science*, 2024. It is not a research platform, not a
Habermasian discourse-ethics implementation, and not a deliberation
product. Features that drift toward any of those are politely declined
in review. The roadmap entry for each phase lives in the README; if your
change exceeds the current phase's scope, the right move is to discuss
in an issue first.

## Local development

You need Python 3.12+, Node 20+, and `git`.

```bash
# Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # full suite — should be 22 green
habermas-mirror serve        # uvicorn on http://127.0.0.1:8000

# In a second shell — Vite dev server
cd web
npm install
npm run dev                  # http://localhost:5173 — proxies /api to backend
```

`pytest` runs both the unit suite and the release-invariants suite
(`tests/test_release_invariants.py`). The release-invariants suite is
the mechanical guard against the kind of stale-documentation drift the
project has already had to fix twice; please leave it in place.

### Running against a real LLM provider

Set `HABERMAS_MIRROR_MODEL` and the matching provider key:

```bash
export HABERMAS_MIRROR_MODEL=openai/gpt-4o-mini   # or anthropic/..., gemini/..., etc.
export OPENAI_API_KEY=...                          # or ANTHROPIC_API_KEY, GEMINI_API_KEY, ...
habermas-mirror serve
```

Without those, every facilitate run returns deterministic mock output
with the prefix `[MOCK]` so you can develop and test without
spending tokens or trusting Claude/Anthropic/this project with a real
key. The mock fingerprints prompts via SHA-256, but never echoes prompt
content into the response.

## Style

- Python: ruff lint (configured in `pyproject.toml`), black-compatible
  formatting via the formatter your editor is wired to. Keep functions
  short and named for the thing they actually do.
- TypeScript: the build runs `tsc --noEmit` with strict mode and
  `noUnusedLocals`/`noUnusedParameters`. The frontend deliberately
  avoids a UI framework or state library.
- Commit messages: one-line subject, blank line, prose body. Reference
  the phase you are working in (e.g. `feat(api): Phase 1 — ...`) so the
  README roadmap guard can do its job.

## Pull requests

- One change per PR; small is easier to review honestly.
- Update `CHANGELOG.md` under the *Unreleased* heading.
- Lockfile (`web/package-lock.json`) changes should go in a dedicated
  commit so review attention can focus on actual code changes.

## Known gaps before 0.1.0

These are known limitations of the 0.0.1 release that we will accept
PRs for, in priority order:

- **Security response headers on the static-mount path.** When the
  backend serves `web/dist` as `StaticFiles`, it does not add
  `X-Content-Type-Options`, `X-Frame-Options`, or a Content-Security-
  Policy header. Self-hosters exposing the app to anyone they didn't
  personally pick should put it behind a reverse proxy that does, or
  contribute a small `SecureHeaders` middleware.
- **Accessibility.** The Vite UI uses `placeholder`-only inputs for
  author and opinion body; explicit `<label>` association is welcome.
- **Idempotency / rate-limit on `POST /api/sessions/{id}/facilitate`.**
  Each call fires three LLM requests; the endpoint does not currently
  short-circuit duplicate calls or enforce a per-session cap.

## What we explicitly will not accept

- Code or docs claiming `habermas-mirror` implements Habermasian
  discourse ethics, scores sincerity, detects strategic action, or
  preserves dissent as a first-class object. Those were deliberately
  scoped out; see [`docs/BFT_NOTE.md`](./docs/BFT_NOTE.md) and the
  README *Non-goals* section for the rationale.
- Features that introduce a heavy dependency (TweetyProject, Argdown,
  sqlite-vec, vector stores, ORMs) for marginal benefit. The bar is
  high — propose it in an issue first.
- Forks or vendored code from AGPL-licensed projects (Pol.is, Decidim,
  Loomio). The project is Apache-2.0 and intends to stay that way.

## Sunset

If, six months after the first tagged release, the project has fewer
than 10 GitHub stars AND fewer than 3 forks, this repository will be
archived rather than maintained as bit-rot. Contributors should know
this going in.
