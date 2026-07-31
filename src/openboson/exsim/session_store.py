"""Persist in-progress / paused ExSim sessions to SQLite.

One active (``in_progress`` or ``paused``) exam per user is supported. Snapshots
are stored as JSON on ``exam_sessions.state_json`` so question order and
presentation survive app restart without re-sampling blueprints.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from openboson.bank_schema import Question
from openboson.db import get_sessionmaker, init_db
from openboson.exsim.scoring import ExamResult
from openboson.exsim.session import ExamSession, SessionStatus
from openboson.models import ExamSession as ExamSessionORM
from openboson.models import User, UserAnswer

logger = logging.getLogger(__name__)

_ACTIVE = (SessionStatus.IN_PROGRESS.value, SessionStatus.PAUSED.value)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        # Prefer an engine already bound by stats_service / tests.
        try:
            from openboson import stats_service

            if getattr(stats_service, "_engine", None) is not None:
                _engine = stats_service._engine
                return _engine
        except Exception:
            pass
        _engine = init_db()
    return _engine


def _db() -> Session:
    return get_sessionmaker(_get_engine())()


def _default_user(s: Session) -> User:
    user = s.query(User).first()
    if user is None:
        user = User(display_name="Default")
        s.add(user)
        s.flush()
    return user


@dataclass(frozen=True)
class ResumableSessionInfo:
    """Lightweight metadata for Dashboard / API list views."""

    engine_session_id: str
    exam_code: str
    exam_version: str
    exam_title: str
    status: str
    current_index: int
    question_count: int
    remaining_seconds: int | None
    blueprint_id: str | None
    started_at: datetime | None
    paused_at: datetime | None
    answered_count: int


def upsert_active_session(session: ExamSession) -> int:
    """Insert or update the active row for ``session``. Returns ORM id."""
    if session.status not in (SessionStatus.IN_PROGRESS, SessionStatus.PAUSED):
        raise ValueError(f"upsert_active_session expects active status, got {session.status}")
    snap = session.to_snapshot()
    now = datetime.now(UTC)
    with _db() as s:
        user = _default_user(s)
        # Only one active attempt per user.
        others = (
            s.query(ExamSessionORM)
            .filter(
                ExamSessionORM.user_id == user.id,
                ExamSessionORM.status.in_(_ACTIVE),
                ExamSessionORM.engine_session_id != session.session_id,
            )
            .all()
        )
        for row in others:
            row.status = SessionStatus.ABANDONED.value
            row.state_json = None
            row.last_active_at = now

        orm = (
            s.query(ExamSessionORM)
            .filter(ExamSessionORM.engine_session_id == session.session_id)
            .first()
        )
        if orm is None:
            orm = ExamSessionORM(
                user_id=user.id,
                exam_id=None,
                exam_code=session.exam.code,
                exam_version=session.exam.version,
                mode=str(session.mode),
                started_at=session.started_at,
                engine_session_id=session.session_id,
            )
            s.add(orm)

        orm.exam_code = session.exam.code
        orm.exam_version = session.exam.version
        orm.mode = str(session.mode)
        orm.status = str(session.status)
        orm.blueprint_id = session.blueprint_id
        orm.current_index = session.current_index
        orm.remaining_seconds = session.remaining_seconds
        orm.paused_at = session.paused_at
        orm.last_active_at = now
        orm.state_json = json.dumps(snap)
        orm.finished_at = None
        orm.score = None
        orm.passed = None
        s.commit()
        return int(orm.id)


def abandon_active_sessions() -> int:
    """Mark all in-progress/paused sessions abandoned. Returns count."""
    now = datetime.now(UTC)
    with _db() as s:
        user = _default_user(s)
        rows = (
            s.query(ExamSessionORM)
            .filter(ExamSessionORM.user_id == user.id, ExamSessionORM.status.in_(_ACTIVE))
            .all()
        )
        for row in rows:
            row.status = SessionStatus.ABANDONED.value
            row.state_json = None
            row.last_active_at = now
        s.commit()
        return len(rows)


def get_resumable_info() -> ResumableSessionInfo | None:
    """Return metadata for the latest resumable session, if any."""
    with _db() as s:
        user = _default_user(s)
        row = (
            s.query(ExamSessionORM)
            .filter(ExamSessionORM.user_id == user.id, ExamSessionORM.status.in_(_ACTIVE))
            .order_by(ExamSessionORM.id.desc())
            .first()
        )
        if row is None or not row.engine_session_id or not row.state_json:
            return None
        try:
            snap = json.loads(row.state_json)
        except json.JSONDecodeError:
            return None
        answers = snap.get("answers") or {}
        answered = sum(
            1 for a in answers.values() if isinstance(a, dict) and a.get("answer") is not None
        )
        return ResumableSessionInfo(
            engine_session_id=row.engine_session_id,
            exam_code=row.exam_code or str(snap.get("exam_code") or ""),
            exam_version=row.exam_version or str(snap.get("exam_version") or ""),
            exam_title=str(snap.get("exam_title") or row.exam_code or "Exam"),
            status=row.status,
            current_index=int(row.current_index or 0),
            question_count=len(snap.get("question_ids") or []),
            remaining_seconds=row.remaining_seconds,
            blueprint_id=row.blueprint_id,
            started_at=row.started_at,
            paused_at=row.paused_at,
            answered_count=answered,
        )


def list_resumable_sessions() -> list[ResumableSessionInfo]:
    info = get_resumable_info()
    return [info] if info is not None else []


def load_active_session(
    questions_by_id: dict[str, Question],
    *,
    engine_session_id: str | None = None,
) -> ExamSession | None:
    """Load and rebuild the resumable session from SQLite."""
    return _load_session(
        questions_by_id,
        engine_session_id=engine_session_id,
        statuses=_ACTIVE,
    )


def load_session_by_id(
    questions_by_id: dict[str, Question],
    engine_session_id: str,
) -> ExamSession | None:
    """Load a session by engine id regardless of status (for review / resume)."""
    return _load_session(
        questions_by_id,
        engine_session_id=engine_session_id,
        statuses=None,
    )


def _load_session(
    questions_by_id: dict[str, Question],
    *,
    engine_session_id: str | None,
    statuses: tuple[str, ...] | None,
) -> ExamSession | None:
    with _db() as s:
        user = _default_user(s)
        q = s.query(ExamSessionORM).filter(ExamSessionORM.user_id == user.id)
        if statuses is not None:
            q = q.filter(ExamSessionORM.status.in_(statuses))
        if engine_session_id:
            q = q.filter(ExamSessionORM.engine_session_id == engine_session_id)
        row = q.order_by(ExamSessionORM.id.desc()).first()
        if row is None or not row.state_json:
            return None
        try:
            snap = json.loads(row.state_json)
        except json.JSONDecodeError:
            logger.warning("Corrupt state_json for exam session %s", row.id)
            return None
    try:
        return ExamSession.from_snapshot(snap, questions_by_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to restore exam session: %s", exc, exc_info=True)
        return None


def finalize_session(session: ExamSession, result: ExamResult) -> int:
    """Mark the matching row finished and write per-question answers.

    Creates a new finished row when no engine_session_id match exists (legacy path).
    """
    from openboson.models import Exam

    snap = session.to_snapshot()
    exam_code = (result.exam_code or session.exam.code or "").strip()
    exam_version = (result.exam_version or session.exam.version or "").strip()
    now = datetime.now(UTC)
    with _db() as s:
        user = _default_user(s)
        exam_row = s.query(Exam).filter(Exam.exam_code == exam_code).first() if exam_code else None
        orm = (
            s.query(ExamSessionORM)
            .filter(ExamSessionORM.engine_session_id == session.session_id)
            .first()
        )
        if orm is None:
            orm = ExamSessionORM(
                user_id=user.id,
                exam_id=exam_row.id if exam_row else None,
                exam_code=exam_code,
                exam_version=exam_version,
                mode=result.mode,
                started_at=session.started_at,
                engine_session_id=session.session_id,
            )
            s.add(orm)
            s.flush()
        else:
            # Drop any prior answer rows if re-finalizing.
            for ans in list(orm.answers):
                s.delete(ans)

        orm.exam_id = exam_row.id if exam_row else orm.exam_id
        orm.exam_code = exam_code
        orm.exam_version = exam_version
        orm.mode = result.mode
        orm.started_at = session.started_at
        orm.finished_at = session.finished_at or now
        orm.score = result.score
        orm.passed = result.passed
        orm.status = SessionStatus.FINISHED.value
        orm.blueprint_id = session.blueprint_id
        orm.current_index = session.current_index
        orm.remaining_seconds = session.remaining_seconds
        orm.paused_at = None
        orm.last_active_at = now
        orm.state_json = json.dumps(snap)
        orm.engine_session_id = session.session_id

        for q in session.questions:
            ua = session.answers.get(q.id)
            ans_json = json.dumps(ua.answer) if ua and ua.answer is not None else "[]"
            is_correct = ua.is_correct if ua else None
            cert_tag = q.cert_tags[0] if q.cert_tags else ""
            s.add(
                UserAnswer(
                    session_id=orm.id,
                    question_id=None,
                    bank_question_id=q.id,
                    topic_code=q.topic_code or "",
                    cert_tag=cert_tag,
                    exam_version=exam_version,
                    answer_json=ans_json,
                    is_correct=is_correct,
                    time_spent_seconds=int(ua.time_spent_seconds) if ua else 0,
                )
            )
        s.commit()
        return int(orm.id)


def peek_snapshot(engine_session_id: str) -> dict[str, Any] | None:
    """Return raw snapshot JSON for tests / diagnostics."""
    with _db() as s:
        row = (
            s.query(ExamSessionORM)
            .filter(ExamSessionORM.engine_session_id == engine_session_id)
            .first()
        )
        if row is None or not row.state_json:
            return None
        try:
            data = json.loads(row.state_json)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
