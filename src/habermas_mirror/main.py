"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from habermas_mirror import __version__
from habermas_mirror.api import opinions
from habermas_mirror.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="habermas-mirror",
        version=__version__,
        description=(
            "Self-hostable reference re-implementation of the prompted "
            "Habermas Machine deliberation facilitator pipeline."
        ),
    )
    init_db()
    app.include_router(opinions.router, prefix="/api", tags=["sessions"])

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
