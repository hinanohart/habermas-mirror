"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from habermas_mirror import __version__
from habermas_mirror.api import facilitate, opinions
from habermas_mirror.db import init_db


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
    app.include_router(opinions.router, prefix="/api", tags=["sessions"])
    app.include_router(facilitate.router, prefix="/api", tags=["facilitate"])

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
