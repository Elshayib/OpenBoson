"""In-process engine facade for the OpenBoson GUI.

The GUI calls engine modules directly (no HTTP server). This module wraps
bank loading and exam-session management behind a small, GUI-friendly API so
pages don't import engine internals directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openboson.bank_loader import BankLoaderError, load_exam_bank
from openboson.bank_schema import ExamBank
from openboson.exsim.scoring import ExamResult, score_exam
from openboson.exsim.session import ExamMode, ExamSession

# Default banks shipped with the repo: <repo>/data/demo_banks
_DEFAULT_BANKS_DIR = Path(__file__).resolve().parents[3] / "data" / "demo_banks"


def load_available_banks() -> list[ExamBank]:
    """Load all YAML banks from the bundled demo banks dir (best-effort)."""
    banks: list[ExamBank] = []
    if not _DEFAULT_BANKS_DIR.is_dir():
        return banks
    for path in sorted(_DEFAULT_BANKS_DIR.glob("*.yaml")):
        try:
            banks.append(load_exam_bank(path))
        except BankLoaderError:
            # Skip malformed banks; the GUI just won't show them.
            continue
    return banks


def get_exam_by_code(code: str) -> ExamBank | None:
    for bank in load_available_banks():
        if bank.code == code:
            return bank
    return None


def start_session(bank: ExamBank, mode: ExamMode = ExamMode.TIMED) -> ExamSession:
    """Create and return a fresh exam session for the given bank."""
    return ExamSession.create(bank, mode=mode)


def finish_and_score(session: ExamSession) -> ExamResult:
    """Finish a session and compute its result."""
    if not session.is_finished():
        session.finish()
    return score_exam(session)
