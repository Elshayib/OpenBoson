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
    try:
        from importlib.metadata import version

        return version("openboson")
    except Exception:
        return _version_from_pyproject()


__version__ = _resolve_version()
