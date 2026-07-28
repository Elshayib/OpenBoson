"""In-process engine facade for the OpenBoson GUI.

The GUI calls engine modules directly (no HTTP server). This module wraps
bank/lab loading and exam/lab-session management behind a small, GUI-friendly
API so pages don't import engine internals directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openboson.bank_loader import BankLoaderError, load_exam_bank
from openboson.bank_schema import ExamBank
from openboson.exsim.scoring import ExamResult, score_exam
from openboson.exsim.session import ExamMode, ExamSession
from openboson.netsim.lab_loader import LabLoaderError, load_lab
from openboson.netsim.lab_schema import LabBank
from openboson.netsim.session import LabResult, LabSession, score_lab

# Default content shipped with the repo: <repo>/data/...
_DEFAULT_BANKS_DIR = Path(__file__).resolve().parents[3] / "data" / "demo_banks"
_DEFAULT_LABS_DIR = Path(__file__).resolve().parents[3] / "data" / "demo_labs"


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


# -----/ NetSim facade /-----
def load_available_labs() -> list[LabBank]:
    """Load all YAML labs from the bundled demo labs dir (best-effort)."""
    labs: list[LabBank] = []
    if not _DEFAULT_LABS_DIR.is_dir():
        return labs
    for path in sorted(_DEFAULT_LABS_DIR.glob("*.yaml")):
        try:
            labs.append(load_lab(path))
        except LabLoaderError:
            continue
    return labs


def get_lab_by_id(lab_id: str) -> LabBank | None:
    for lab in load_available_labs():
        if lab.lab_id == lab_id:
            return lab
    return None


def start_lab_session(lab: LabBank) -> LabSession:
    """Create and return a fresh lab session for the given lab."""
    return LabSession.create(lab)


def finish_and_score_lab(session: LabSession) -> LabResult:
    """Finish a lab session and compute its result."""
    if not session.is_finished():
        session.finish()
    return score_lab(session)
