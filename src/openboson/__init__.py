"""OpenBoson — open-source local ExSim + NetSim practice platform."""

from __future__ import annotations

from pathlib import Path


def _version_from_pyproject() -> str:
    """Fallback for editable/source trees where metadata may be unavailable."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        return "0.0.0"

    # src/openboson/__init__.py -> repo root
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return "0.0.0"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data.get("project", {}).get("version", "0.0.0"))


def _resolve_version() -> str:
    # Packaged builds stamp the release version explicitly.
    try:
        from openboson import _build_info

        packaged = getattr(_build_info, "PACKAGED_VERSION", None)
        if packaged:
            return str(packaged)
    except Exception:
        pass

    # Prefer pyproject when running from a source/editable tree so the UI
    # matches the checkout instead of stale dist-info (e.g. an old pip install).
    file_ver = _version_from_pyproject()
    if file_ver != "0.0.0":
        return file_ver

    try:
        from importlib.metadata import version

        return version("openboson")
    except Exception:
        return "0.0.0"


__version__ = _resolve_version()
