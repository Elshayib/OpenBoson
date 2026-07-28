"""Persistence service — bridges in-memory sessions to SQLite.

Called by the GUI engine when an exam or lab finishes. Also provides
read-side queries for the Stats page (history, per-domain aggregates).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from openboson.db import get_engine, get_sessionmaker, init_db
from openboson.exsim.scoring import ExamResult
from openboson.exsim.session import ExamSession
from openboson.models import (
    ExamSession as ExamSessionORM,
    LabSession as LabSessionORM,
    LabStep,
    User,
    UserAnswer,
)
from openboson.netsim.session import LabResult, LabSession

_engine = None


def _get_engine():
    """Lazily init the shared engine (once per process)."""
    global _engine
    if _engine is None:
        _engine = init_db()
    return _engine


def _session() -> Session:
    return get_sessionmaker(_get_engine())()


# -----/ Users /-----
def get_or_create_default_user(display_name: str = "Default") -> User:
    """Return the first user row, creating one if the table is empty."""
    with _session() as s:
        user = s.query(User).first()
        if user is None:
            user = User(display_name=display_name)
            s.add(user)
            s.commit()
        else:
            s.refresh(user)
        # Detach so the object is usable after session close.
        s.expunge(user)
        return user


# -----/ Exam persistence /-----
def save_exam_result(session: ExamSession, result: ExamResult) -> int:
    """Persist a finished exam session + per-question answers.

    Returns the DB row id of the ExamSession.
    """
    user = get_or_create_default_user()
    with _session() as s:
        orm = ExamSessionORM(
            user_id=user.id,
            exam_id=_exam_id_or_zero(s, result.exam_code),
            mode=result.mode,
            started_at=session.started_at,
            finished_at=session.finished_at or datetime.now(timezone.utc),
            score=result.score,
            passed=result.passed,
        )
        s.add(orm)
        s.flush()  # get orm.id
        for q in session.questions:
            ua = session.answers.get(q.id)
            ans_json = json.dumps(ua.answer) if ua and ua.answer is not None else "[]"
            is_correct = ua.is_correct if ua else None
            s.add(
                UserAnswer(
                    session_id=orm.id,
                    question_id=0,  # questions aren't persisted as rows yet
                    answer_json=ans_json,
                    is_correct=is_correct,
                    time_spent_seconds=int(ua.time_spent_seconds) if ua else 0,
                )
            )
        s.commit()
        return orm.id


def _exam_id_or_zero(s: Session, exam_code: str) -> int:
    """We don't persist Exam rows for bundled banks yet; use 0 as sentinel."""
    return 0


# -----/ Lab persistence /-----
def save_lab_result(session: LabSession, result: LabResult) -> int:
    """Persist a finished lab session + per-task steps.

    Returns the DB row id of the LabSession.
    """
    user = get_or_create_default_user()
    with _session() as s:
        orm = LabSessionORM(
            user_id=user.id,
            lab_id=session.lab.lab_id,
            started_at=session.started_at,
            finished_at=session.finished_at or datetime.now(timezone.utc),
            status="completed",
            score=result.score,
        )
        s.add(orm)
        s.flush()
        for idx, (tid, grade) in enumerate(result.task_grades.items()):
            s.add(
                LabStep(
                    lab_session_id=orm.id,
                    step_index=idx,
                    expected_config="",
                    submitted_config=grade.submitted_config,
                    is_correct=grade.is_correct,
                    feedback=grade.feedback,
                )
            )
        s.commit()
        return orm.id


# -----/ Read side: Stats queries /-----
@dataclass
class ExamHistoryItem:
    id: int
    exam_code: str
    mode: str
    score: float
    passed: bool
    finished_at: datetime | None


@dataclass
class LabHistoryItem:
    id: int
    lab_id: str
    score: float
    finished_at: datetime | None


@dataclass
class DomainAggregate:
    """Aggregate stats for one CCNA domain prefix (e.g. '1.')."""
    domain_prefix: str
    total_questions: int
    correct: int
    weight: float = 0.0

    @property
    def percent(self) -> float:
        return self.correct / self.total_questions if self.total_questions else 0.0


def exam_history(limit: int = 50) -> list[ExamHistoryItem]:
    """Recent exam attempts, newest first."""
    with _session() as s:
        rows = (
            s.query(ExamSessionORM)
            .order_by(ExamSessionORM.finished_at.desc())
            .limit(limit)
            .all()
        )
        return [
            ExamHistoryItem(
                id=r.id,
                exam_code=f"exam-{r.exam_id}",
                mode=r.mode,
                score=r.score or 0.0,
                passed=r.passed or False,
                finished_at=r.finished_at,
            )
            for r in rows
        ]


def lab_history(limit: int = 50) -> list[LabHistoryItem]:
    with _session() as s:
        rows = (
            s.query(LabSessionORM)
            .order_by(LabSessionORM.finished_at.desc())
            .limit(limit)
            .all()
        )
        return [
            LabHistoryItem(
                id=r.id,
                lab_id=r.lab_id,
                score=r.score or 0.0,
                finished_at=r.finished_at,
            )
            for r in rows
        ]


def exam_summary() -> dict[str, Any]:
    """High-level aggregate stats for the Stats page."""
    with _session() as s:
        total = s.query(ExamSessionORM).count()
        passed = s.query(ExamSessionORM).filter(ExamSessionORM.passed.is_(True)).count()
        avg_score = 0.0
        if total > 0:
            scores = [r.score or 0.0 for r in s.query(ExamSessionORM).all()]
            avg_score = sum(scores) / len(scores) if scores else 0.0
        return {
            "total_exams": total,
            "passed": passed,
            "avg_score": avg_score,
        }


def lab_summary() -> dict[str, Any]:
    with _session() as s:
        total = s.query(LabSessionORM).count()
        avg_score = 0.0
        if total > 0:
            scores = [r.score or 0.0 for r in s.query(LabSessionORM).all()]
            avg_score = sum(scores) / len(scores) if scores else 0.0
        return {
            "total_labs": total,
            "avg_score": avg_score,
        }
