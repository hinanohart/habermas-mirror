"""FastAPI application entrypoint."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from habermas_mirror import __version__
from habermas_mirror.api import facilitate, opinions
from habermas_mirror.db import init_db

# Dev origins for the Vite frontend (Phase 3). Production self-host
# operators should override via configuration, not by widening this list.
_DEFAULT_DEV_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="habermas-mirror",
        version=__version__,
        description=(
            "Self-hostable reference re-implementation of the prompted "
            "Habermas Machine deliberation facilitator pipeline."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_DEFAULT_DEV_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(opinions.router, prefix="/api", tags=["sessions"])
    app.include_router(facilitate.router, prefix="/api", tags=["facilitate"])

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    dist = _locate_web_dist()
    if dist is not None:
        # Mount LAST so the API routes above take precedence. `html=True`
        # makes StaticFiles serve `index.html` for any path that doesn't
        # match a file — the single-page React app handles its own routing.
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")

    return app


def _locate_web_dist() -> Path | None:
    """Return the directory containing the built React UI, if any.

    Search order:

    1. ``HABERMAS_MIRROR_WEB_DIST`` env var (operator override).
    2. ``<repo>/web/dist`` (the standard layout this repository uses).
    3. ``<cwd>/web/dist`` (when running from an unpacked source tree).

    Returns ``None`` if no bundle is present; in that case the API still
    serves and the operator can run the Vite dev server separately or
    deploy the static bundle behind their own reverse proxy.
    """
    candidates: list[Path] = []
    env_override = os.environ.get("HABERMAS_MIRROR_WEB_DIST")
    if env_override:
        candidates.append(Path(env_override))
    candidates.append(Path(__file__).resolve().parents[2] / "web" / "dist")
    candidates.append(Path.cwd() / "web" / "dist")
    for c in candidates:
        if c.is_dir() and (c / "index.html").is_file():
            return c
    return None


app = create_app()
