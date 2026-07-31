"""Loader for OpenBoson question banks in YAML format."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from openboson.bank_schema import (
    ExamBank,
    Question,
    QuestionPool,
    Topic,
    normalize_legacy_bank_dict,
)


class BankLoaderError(Exception):
    """Raised when a question bank fails to load or validate."""


@dataclass(frozen=True)
class BankLoadDiagnostic:
    """One rejected (or noted) bank file with a human-readable reason."""

    path: str
    reason: str


@dataclass
class BankLoadResult:
    """Outcome of loading a directory of bank YAML files."""

    banks: list[ExamBank] = field(default_factory=list)
    rejected: list[BankLoadDiagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.rejected


def load_exam_bank(path_or_text: str | Path) -> ExamBank:
    """Load an exam bank from a YAML path or YAML string.

    - If the input is a path to an existing ``.yaml`` / ``.yml`` file, read it.
    - Otherwise, treat the input as raw YAML text.
    """
    raw = _read_yaml(path_or_text)
    if not isinstance(raw, dict):
        raise BankLoaderError("Bank YAML root must be a mapping, got " + type(raw).__name__)
    try:
        normalized = normalize_legacy_bank_dict(raw)
        return ExamBank.model_validate(normalized)
    except Exception as exc:
        raise BankLoaderError(f"Failed to validate exam bank: {exc}") from exc


def load_banks_from_dir(
    directory: str | Path,
    *,
    best_effort: bool = True,
) -> list[ExamBank]:
    """Load every ``*.yaml`` / ``*.yml`` bank in ``directory`` (sorted by name).

    When ``best_effort`` is True (default), invalid files are skipped. Use
    :func:`load_banks_detailed` to inspect rejection reasons. When False, the
    first failure raises :class:`BankLoaderError`.
    """
    return load_banks_detailed(directory, best_effort=best_effort).banks


def load_banks_detailed(
    directory: str | Path,
    *,
    best_effort: bool = True,
) -> BankLoadResult:
    """Load banks from a directory and return accepted banks plus diagnostics."""
    root = Path(directory)
    result = BankLoadResult()
    if not root.is_dir():
        return result

    paths = sorted(list(root.glob("*.yaml")) + list(root.glob("*.yml")))
    for path in paths:
        try:
            result.banks.append(load_exam_bank(path))
        except BankLoaderError as exc:
            diagnostic = BankLoadDiagnostic(path=str(path), reason=str(exc))
            result.rejected.append(diagnostic)
            if not best_effort:
                raise BankLoaderError(f"Failed to load bank {path.name}: {exc}") from exc
    return result


def merge_banks(banks: list[ExamBank]) -> QuestionPool:
    """Merge multiple banks into one question pool.

    Duplicate question ids keep the first occurrence. Topics are de-duplicated
    by code (first wins).
    """
    seen_q: set[str] = set()
    questions: list[Question] = []
    topics_by_code: dict[str, Topic] = {}
    source_codes: list[str] = []

    for bank in banks:
        source_codes.append(bank.code)
        for topic in bank.topics:
            topics_by_code.setdefault(topic.code, topic)
        for q in bank.questions:
            if q.id in seen_q:
                continue
            seen_q.add(q.id)
            questions.append(q)

    return QuestionPool(
        questions=questions,
        topics=list(topics_by_code.values()),
        source_codes=source_codes,
    )


def load_question_pool(directory: str | Path, *, best_effort: bool = True) -> QuestionPool:
    """Load and merge all banks under ``directory``."""
    return merge_banks(load_banks_from_dir(directory, best_effort=best_effort))


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
