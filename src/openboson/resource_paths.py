"""Resolve bundled application resources across source, wheel, and frozen layouts."""

from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    """Return the ``openboson`` package directory."""
    return Path(__file__).resolve().parent


def is_frozen() -> bool:
    """True when running inside a PyInstaller (or similar) frozen bundle."""
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def _meipass() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return None


def repo_root() -> Path | None:
    """Return the repository root when running from a source/editable checkout."""
    if is_frozen():
        return None
    # src/openboson/resource_paths.py -> parents[2] == repo root
    candidate = package_root().parents[1]
    if (candidate / "pyproject.toml").is_file() and (candidate / "data").is_dir():
        return candidate
    return None


def bundled_data_dir() -> Path:
    """Directory containing shipped ``demo_banks`` / ``demo_labs`` content."""
    meipass = _meipass()
    if meipass is not None:
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (
            meipass / "data",
            meipass,
            exe_dir / "data",
            exe_dir / "_internal" / "data",
        ):
            if (candidate / "demo_banks").is_dir() or (candidate / "demo_labs").is_dir():
                return candidate

    root = repo_root()
    if root is not None:
        data = root / "data"
        if data.is_dir():
            return data

    # Wheel / site-packages layout: package-adjacent or package-local data.
    pkg = package_root()
    for candidate in (pkg / "data", pkg.parent.parent / "data"):
        if candidate.is_dir():
            return candidate

    # Last resort: keep a stable path for callers even if empty.
    return pkg / "data"


def bundled_banks_dir() -> Path:
    return bundled_data_dir() / "demo_banks"


def bundled_labs_dir() -> Path:
    return bundled_data_dir() / "demo_labs"


def gui_styles_path() -> Path:
    """Path to the shipped Qt stylesheet."""
    meipass = _meipass()
    if meipass is not None:
        for candidate in (
            meipass / "openboson" / "gui" / "styles.qss",
            meipass / "gui" / "styles.qss",
            package_root() / "gui" / "styles.qss",
        ):
            if candidate.is_file():
                return candidate
    return package_root() / "gui" / "styles.qss"
