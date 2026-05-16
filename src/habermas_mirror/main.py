"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    return app


app = create_app()
