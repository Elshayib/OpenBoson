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

    # Mount ExSim routes. Importing here avoids a cycle with the engine
    # modules that may need server-side helpers in the future.
    from openboson.exsim.router import _ROUTER as exsim_router

    app.include_router(exsim_router)

    from openboson.netsim.router import _ROUTER as netsim_router

    app.include_router(netsim_router)

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
