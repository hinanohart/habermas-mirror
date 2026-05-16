# Release notes — habermas-mirror 0.0.1 (draft)

> This file is the draft notes for the eventual first tagged release.
> Until that tag exists, treat the project as pre-alpha. The notes here
> are written from the assumption that what is in `main` today is what
> ships as 0.0.1.

## What this is

`habermas-mirror` is a self-hostable, multi-provider re-implementation
of the *prompted* deliberation facilitator described in:

> Tessler, M. H., Bakker, M., Jarrett, D., et al.
> *AI can help humans find common ground in democratic deliberation.*
> Science, 2024. <https://doi.org/10.1126/science.adq2852>

DeepMind's [reference repository](https://github.com/google-deepmind/habermas_machine)
provides the Gemini-only prompted variant; `habermas-mirror` provides
the same prompted pipeline behind a small FastAPI app, with LiteLLM in
the middle so any major provider works, and with a minimal React UI for
the typical "submit-opinions-then-facilitate" loop.

## What is in 0.0.1

- Backend: Python 3.12 + FastAPI + SQLite + LiteLLM. Three LLM stages
  (draft → critique → refine) persisted to a `statements` table for
  later audit.
- Frontend: a single Vite + React + TypeScript bundle. ~150 lines of
  hand-rolled CSS; no UI framework or state library.
- CLI: `habermas-mirror serve` launches uvicorn on `127.0.0.1:8000`.
- Single-process serve path: when `web/dist/` exists, the FastAPI app
  mounts it as a static directory so the same process answers both
  `/api/*` and `/`. Otherwise the API serves alone and the frontend can
  be deployed behind any static host.
- 26 tests (`pytest`) covering API plumbing, the four-stage pipeline
  with both mock and patched-LiteLLM paths (attribute and dict shape),
  pipeline atomicity (no orphan stage-1 rows on stage-2 failure), the
  shared `run_id` correlation column, CORS, the static-mount glue when
  the bundle is present, the `/api/{rest:path}` JSON 404 catch-all,
  and five release-invariant guards on the README and `pyproject.toml`.

## What this is **not**

- An implementation of Habermasian discourse ethics. The contested
  Habermas-philosophy critiques of the original Habermas Machine
  (Volpe 2025; CACM "Ghost in the Habermas Machine"; TRISE 2026-03)
  apply to this project too. It is an engineering re-implementation,
  nothing more.
- A consensus mechanism. Running the pipeline through a single LLM
  provider is structurally equivalent to a single-party attestation;
  see [`docs/BFT_NOTE.md`](./docs/BFT_NOTE.md) for the honest version.
- A research artefact with novelty claims. The four differentiation
  axes considered during scoping (4-validity classifier, sincerity
  detection, dissent preservation as a first-class object, audit-of-
  audit) all have prior art as of 2026 and were deliberately scoped out
  of this project to keep it small.

## Knobs

| env var | effect |
| --- | --- |
| `HABERMAS_MIRROR_MODEL` | LiteLLM model string. *Required* for any real LLM call; without it, the pipeline returns deterministic mocks. |
| `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`, `AZURE_API_KEY`) | Provider credential. LiteLLM reads these directly from the environment. |
| `HABERMAS_MIRROR_DB` | SQLite database path. Defaults to `./habermas-mirror.db`. |
| `HABERMAS_MIRROR_WEB_DIST` | Override for the static-bundle location. Defaults to `<repo>/web/dist` or `<cwd>/web/dist` if either exists. |

## Sunset

If this project has fewer than 10 GitHub stars AND fewer than 3 forks
six months after this tag, the repository will be archived rather than
maintained as bit-rot. If DeepMind (or anyone else) publishes a more
complete self-hostable re-implementation of the Habermas Machine, this
project will redirect users there.

## Publishing

This is a local-only release draft. When the maintainer is ready to
tag 0.0.1 publicly:

```bash
git tag -a v0.0.1 -m "habermas-mirror 0.0.1"
git push origin main v0.0.1
# (GitHub Release UI or `gh release create v0.0.1 -F RELEASE_NOTES.md`)
```

The publishing step is intentionally outside the automated build path
of this repository: it requires the maintainer to authenticate to
GitHub interactively, and Apache-2.0-licensed code being put under
someone's name is a deliberate human decision, not an autonomous one.
