"""Loader for OpenBoson lab definitions in YAML format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from openboson.netsim.lab_schema import LabBank


class LabLoaderError(Exception):
    """Raised when a lab fails to load or validate."""


def load_lab(path_or_text: str | Path) -> LabBank:
    """Load a lab from a YAML path or raw YAML text."""
    raw = _read_yaml(path_or_text)
    if not isinstance(raw, dict):
        raise LabLoaderError("Lab YAML root must be a mapping")
    try:
        return LabBank.model_validate(raw)
    except Exception as exc:
        raise LabLoaderError(f"Failed to validate lab: {exc}") from exc


def _read_yaml(source: str | Path) -> Any:
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        path = Path(source)
        if not path.is_file():
            raise LabLoaderError(f"Lab file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    return yaml.safe_load(str(source))
