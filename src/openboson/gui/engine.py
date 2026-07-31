"""In-process engine facade for the OpenBoson GUI.

The GUI calls engine modules directly (no HTTP server). This module wraps
bank/lab loading and exam/lab-session management behind a small, GUI-friendly
API so pages don't import engine internals directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from openboson.bank_loader import BankLoaderError, load_exam_bank
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
from openboson.registry import ContentDiagnostics, get_registry
from openboson.resource_paths import bundled_banks_dir, bundled_labs_dir

logger = logging.getLogger(__name__)

# Non-fatal persistence warning from the last finish_and_score* call (GUI may show it).
last_persistence_warning: str | None = None


def banks_dir() -> Path:
    return bundled_banks_dir()


def labs_dir() -> Path:
    return bundled_labs_dir()


def load_available_banks() -> list[ExamBank]:
    """Load all accepted banks from the content registry."""
    return get_registry().banks()


def load_pool() -> QuestionPool:
    """Load the merged question pool from the content registry."""
    return get_registry().question_pool()


def refresh_content() -> ContentDiagnostics:
    """Rescan banks/labs/packs and return diagnostics."""
    return get_registry().refresh()


def content_diagnostics() -> ContentDiagnostics:
    """Return the latest registry diagnostics (scanning if needed)."""
    return get_registry().diagnostics()


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


def save_active_session(session: ExamSession, *, remaining_seconds: int | None = None) -> None:
    """Persist an in-progress / paused session snapshot (best-effort)."""
    global last_persistence_warning
    try:
        from openboson.exsim import session_store

        if remaining_seconds is not None:
            session.remaining_seconds = max(0, int(remaining_seconds))
        session_store.upsert_active_session(session)
    except Exception as exc:
        last_persistence_warning = f"Could not save exam progress: {exc}"
        logger.warning("Failed to persist active exam session: %s", exc, exc_info=True)


def pause_session(session: ExamSession, remaining_seconds: int | None) -> None:
    """Mark session paused and persist."""
    session.pause(remaining_seconds)
    save_active_session(session)


def resume_session(session: ExamSession) -> None:
    """Mark session in-progress and persist."""
    session.resume()
    save_active_session(session)


def get_resumable_exam_info():
    """Return metadata for a resumable exam, or ``None``."""
    try:
        from openboson.exsim import session_store

        return session_store.get_resumable_info()
    except Exception as exc:
        logger.warning("Failed to query resumable exam: %s", exc, exc_info=True)
        return None


def load_resumable_exam(
    engine_session_id: str | None = None,
    *,
    extra_questions: dict[str, Question] | None = None,
) -> ExamSession | None:
    """Rebuild a paused/in-progress exam from SQLite using the question pool."""
    try:
        from openboson.exsim import session_store

        by_id = dict(load_pool().by_id())
        if extra_questions:
            by_id.update(extra_questions)
        return session_store.load_active_session(
            by_id,
            engine_session_id=engine_session_id,
        )
    except Exception as exc:
        logger.warning("Failed to load resumable exam: %s", exc, exc_info=True)
        return None


def abandon_resumable_exams() -> int:
    try:
        from openboson.exsim import session_store

        return session_store.abandon_active_sessions()
    except Exception as exc:
        logger.warning("Failed to abandon active exams: %s", exc, exc_info=True)
        return 0


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
    "abandon_resumable_exams",
    "banks_dir",
    "blueprint_coverage",
    "finish_and_score",
    "get_blueprint",
    "get_exam_by_code",
    "get_question",
    "get_resumable_exam_info",
    "list_blueprints",
    "load_resumable_exam",
    "content_diagnostics",
    "load_available_banks",
    "load_exam_bank",
    "load_pool",
    "pause_session",
    "refresh_content",
    "resume_session",
    "save_active_session",
    "start_blueprint_exam",
    "start_session",
    # labs
    "ContentDiagnostics",
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
    """Load all accepted labs from the content registry."""
    return get_registry().labs()


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
