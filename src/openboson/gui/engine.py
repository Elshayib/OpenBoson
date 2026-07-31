"""In-process engine facade for the OpenBoson GUI.

The GUI calls engine modules directly (no HTTP server). This module wraps
bank/lab loading and exam/lab-session management behind a small, GUI-friendly
API so pages don't import engine internals directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from openboson.bank_loader import (
    BankLoaderError,
    load_exam_bank,
    load_question_pool,
)
from openboson.bank_schema import ExamBank, Question, QuestionPool
from openboson.exsim.blueprint import (
    InsufficientPoolError,
    bank_from_blueprint,
    build_exam_from_blueprint,
    coverage_for_blueprint,
    get_blueprint,
    list_blueprints,
)
from openboson.exsim.scoring import ExamResult, score_exam
from openboson.exsim.session import ExamMode, ExamSession
from openboson.netsim.lab_loader import LabLoaderError, load_lab
from openboson.netsim.lab_schema import LabBank
from openboson.netsim.session import LabResult, LabSession, score_lab

logger = logging.getLogger(__name__)

# Non-fatal persistence warning from the last finish_and_score* call (GUI may show it).
last_persistence_warning: str | None = None

# Default content shipped with the repo: <repo>/data/...
_DEFAULT_BANKS_DIR = Path(__file__).resolve().parents[3] / "data" / "demo_banks"
_DEFAULT_LABS_DIR = Path(__file__).resolve().parents[3] / "data" / "demo_labs"


def banks_dir() -> Path:
    return _DEFAULT_BANKS_DIR


def load_available_banks() -> list[ExamBank]:
    """Load all YAML banks from the bundled demo banks dir (best-effort)."""
    from openboson.bank_loader import load_banks_detailed

    result = load_banks_detailed(_DEFAULT_BANKS_DIR, best_effort=True)
    for item in result.rejected:
        logger.warning("Skipping bank %s: %s", item.path, item.reason)
    return result.banks


def load_pool() -> QuestionPool:
    """Load the merged question pool from bundled banks."""
    return load_question_pool(_DEFAULT_BANKS_DIR)


def get_exam_by_code(code: str) -> ExamBank | None:
    for bank in load_available_banks():
        if bank.code == code:
            return bank
    return None


def get_question(question_id: str) -> Question | None:
    return load_pool().by_id().get(question_id)


def start_session(bank: ExamBank, mode: ExamMode = ExamMode.EXAM) -> ExamSession:
    """Create and return a fresh exam session for the given bank."""
    return ExamSession.create(bank, mode=mode)


def start_blueprint_exam(blueprint_id: str) -> ExamSession:
    """Sample a blueprint exam from the pool and start an EXAM session.

    Raises :class:`InsufficientPoolError` if the pool cannot fill the blueprint.
    """
    blueprint = get_blueprint(blueprint_id)
    if not blueprint.enabled:
        raise InsufficientPoolError(
            blueprint.coming_soon_label or f"{blueprint.title} is not available yet"
        )
    pool = load_pool()
    questions = build_exam_from_blueprint(pool.questions, blueprint)
    bank = bank_from_blueprint(blueprint, questions)
    return ExamSession.create(
        bank,
        mode=ExamMode.EXAM,
        shuffle=False,
        blueprint_id=blueprint.id,
        questions=questions,
    )


def blueprint_coverage(blueprint_id: str) -> Any:
    blueprint = get_blueprint(blueprint_id)
    return coverage_for_blueprint(load_pool().questions, blueprint)


def finish_and_score(session: ExamSession) -> ExamResult:
    """Finish a session, compute its result, and persist to SQLite."""
    global last_persistence_warning
    last_persistence_warning = None
    if not session.is_finished():
        session.finish()
    result = score_exam(session)
    # Persist (best-effort — don't crash the GUI if the DB is unavailable).
    try:
        from openboson import stats_service

        stats_service.save_exam_result(session, result)
    except Exception as exc:
        last_persistence_warning = f"Could not save exam result: {exc}"
        logger.warning("Failed to persist exam result: %s", exc, exc_info=True)
    return result


# Re-exports for GUI convenience
__all__ = [
    "BankLoaderError",
    "ExamBank",
    "ExamMode",
    "ExamResult",
    "ExamSession",
    "InsufficientPoolError",
    "Question",
    "QuestionPool",
    "banks_dir",
    "blueprint_coverage",
    "finish_and_score",
    "get_blueprint",
    "get_exam_by_code",
    "get_question",
    "list_blueprints",
    "load_available_banks",
    "load_exam_bank",
    "load_pool",
    "start_blueprint_exam",
    "start_session",
    # labs
    "LabBank",
    "LabLoaderError",
    "LabResult",
    "LabSession",
    "finish_and_score_lab",
    "get_lab_by_id",
    "load_available_labs",
    "load_lab",
    "start_lab_session",
]


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
    """Finish a lab session, compute its result, and persist to SQLite."""
    global last_persistence_warning
    last_persistence_warning = None
    if not session.is_finished():
        session.finish()
    result = score_lab(session)
    try:
        from openboson import stats_service

        stats_service.save_lab_result(session, result)
    except Exception as exc:
        last_persistence_warning = f"Could not save lab result: {exc}"
        logger.warning("Failed to persist lab result: %s", exc, exc_info=True)
    return result
