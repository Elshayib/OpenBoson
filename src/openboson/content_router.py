"""Content refresh and diagnostics API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from openboson.registry import get_registry

_ROUTER = APIRouter(prefix="/api/v1", tags=["content"])


@_ROUTER.post("/content/refresh")
def refresh_content() -> dict[str, Any]:
    """Rescan bundled/local/pack content and clear ExSim/NetSim router caches."""
    diagnostics = get_registry().refresh()
    from openboson.exsim import router as exsim_router
    from openboson.netsim import router as netsim_router

    exsim_router.clear_content_cache()
    netsim_router.clear_content_cache()
    return diagnostics.to_dict()


@_ROUTER.get("/content/diagnostics")
def content_diagnostics() -> dict[str, Any]:
    """Return the latest content registry diagnostics (scans if needed)."""
    return get_registry().diagnostics().to_dict()
