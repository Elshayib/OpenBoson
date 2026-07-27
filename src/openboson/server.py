"""FastAPI application — optional HTTP layer for headless use and tests.

The GUI does not need this server; it calls engine modules directly. The HTTP
surface is useful for automated testing, scripting, and a possible future web UI.
"""

from __future__ import annotations

from fastapi import FastAPI

from openboson import __version__


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenBoson Engine",
        version=__version__,
        description="Local ExSim + NetSim engine for OpenBoson.",
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
