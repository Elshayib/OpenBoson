"""OpenBoson — open-source local ExSim + NetSim practice platform."""

from __future__ import annotations

from pathlib import Path


def _version_from_pyproject() -> str:
    """Read version from repo ``pyproject.toml`` when running a classic src layout."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        return "0.0.0"

    # Only trust pyproject for ``<root>/src/openboson/__init__.py`` checkouts.
    pkg = Path(__file__).resolve().parent
    if pkg.name != "openboson" or pkg.parent.name != "src":
        return "0.0.0"
    root = pkg.parent.parent
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return "0.0.0"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict) or project.get("name") != "openboson":
        return "0.0.0"
    return str(project.get("version", "0.0.0"))


def _resolve_version() -> str:
    # Packaged builds stamp the release version explicitly.
    try:
        from openboson import _build_info

        packaged = getattr(_build_info, "PACKAGED_VERSION", None)
        if packaged:
            return str(packaged)
    except Exception:
        pass

    # Prefer pyproject in a verified src checkout so the UI matches the tree
    # instead of stale dist-info from an older pip install.
    file_ver = _version_from_pyproject()
    if file_ver != "0.0.0":
        return file_ver

    try:
        from importlib.metadata import version

        return version("openboson")
    except Exception:
        return "0.0.0"


__version__ = _resolve_version()
