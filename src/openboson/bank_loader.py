"""Loader for OpenBoson question banks in YAML format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from openboson.bank_schema import ExamBank


class BankLoaderError(Exception):
    """Raised when a question bank fails to load or validate."""


def load_exam_bank(path_or_text: str | Path) -> ExamBank:
    """Load an exam bank from a YAML path or YAML string.

    - If the input is a path to an existing ``.yaml`` / ``.yml`` file, read it.
    - Otherwise, treat the input as raw YAML text.
    """
    raw = _read_yaml(path_or_text)
    if not isinstance(raw, dict):
        raise BankLoaderError("Bank YAML root must be a mapping, got " + type(raw).__name__)
    try:
        return ExamBank.model_validate(raw)
    except Exception as exc:
        raise BankLoaderError(f"Failed to validate exam bank: {exc}") from exc


def _read_yaml(source: str | Path) -> Any:
    # Treat as a file path if it exists.
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        path = Path(source)
        if not path.is_file():
            raise BankLoaderError(f"Bank file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    # Otherwise treat as raw YAML.
    return yaml.safe_load(str(source))
