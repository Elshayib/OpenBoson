"""Persistence service — bridges in-memory sessions to SQLite.

Called by the GUI engine when an exam or lab finishes. Also provides
read-side queries for the Stats page (history, per-domain aggregates).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from openboson.db import get_sessionmaker, init_db
from openboson.exsim.scoring import ExamResult
from openboson.exsim.session import ExamSession
from openboson.models import (
    ExamSession as ExamSessionORM,
)
from openboson.models import (
    LabSession as LabSessionORM,
)
from openboson.models import (
    LabStep,
    PracticeAttempt,
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

    Returns the DB row id of the ExamSession. Prefer updating the active
    pause/resume row when ``engine_session_id`` matches.
    """
    from openboson.exsim.session_store import finalize_session

    return finalize_session(session, result)


def _lookup_exam_id(s: Session, exam_code: str) -> int | None:
    """Return a matching Exam row id when one exists; bundled banks usually do not."""
    if not exam_code:
        return None
    from openboson.models import Exam

    row = s.query(Exam).filter(Exam.exam_code == exam_code).first()
    return row.id if row else None


def _display_exam_code(row: ExamSessionORM) -> str:
    """Stable label for history — never ``exam-None``."""
    code = (row.exam_code or "").strip()
    if code:
        return code
    if row.exam_id is not None:
        return f"exam-{row.exam_id}"
    return "unknown"


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
            finished_at=session.finished_at or datetime.now(UTC),
            status="completed",
            score=result.score,
        )
        s.add(orm)
        s.flush()
        for idx, (_tid, grade) in enumerate(result.task_grades.items()):
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
    """Aggregate stats for one exam-domain prefix (e.g. '1.')."""

    domain_prefix: str
    total_questions: int
    correct: int
    weight: float = 0.0
    cert_tag: str | None = None

    @property
    def percent(self) -> float:
        return self.correct / self.total_questions if self.total_questions else 0.0


@dataclass
class ScorePoint:
    """One exam attempt in a score trend series."""

    score: float
    exam_code: str
    finished_at: datetime | None


@dataclass
class DomainVersionCell:
    """Accuracy for one domain prefix under one exam version."""

    domain_prefix: str
    exam_version: str
    correct: int
    total: int

    @property
    def percent(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class DomainTrendPoint:
    """Per-domain accuracy for one finished exam attempt (oldest→newest series)."""

    session_id: int
    exam_code: str
    exam_version: str
    finished_at: datetime | None
    domains: dict[str, float]  # prefix -> percent


_CERT_ALIASES: dict[str, str] = {
    "encor": "ccnp",
    "350-401": "ccnp",
    "200-301": "ccna",
}


def _normalize_cert(cert: str | None) -> str | None:
    if not cert:
        return None
    key = cert.strip().lower()
    return _CERT_ALIASES.get(key, key)


def _domain_prefix(topic_code: str | None) -> str:
    """Roll a topic code (``1.1``) up to a domain prefix (``1.``)."""
    if not topic_code:
        return ""
    head = topic_code.split(".", 1)[0].strip()
    return f"{head}." if head else ""


def exam_history(limit: int = 50) -> list[ExamHistoryItem]:
    """Recent exam attempts, newest first."""
    with _session() as s:
        rows = (
            s.query(ExamSessionORM).order_by(ExamSessionORM.finished_at.desc()).limit(limit).all()
        )
        return [
            ExamHistoryItem(
                id=r.id,
                exam_code=_display_exam_code(r),
                mode=r.mode,
                score=r.score or 0.0,
                passed=r.passed or False,
                finished_at=r.finished_at,
            )
            for r in rows
        ]


def lab_history(limit: int = 50) -> list[LabHistoryItem]:
    with _session() as s:
        rows = s.query(LabSessionORM).order_by(LabSessionORM.finished_at.desc()).limit(limit).all()
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


def domain_totals(cert: str | None = None) -> list[DomainAggregate]:
    """Per-domain correct/total counts from persisted exam answers."""
    cert_n = _normalize_cert(cert)
    with _session() as s:
        q = s.query(UserAnswer).filter(UserAnswer.is_correct.isnot(None))
        if cert_n:
            q = q.filter(UserAnswer.cert_tag == cert_n)
        rows = q.all()

    buckets: dict[str, list[int]] = {}  # prefix -> [correct, total]
    for row in rows:
        prefix = _domain_prefix(row.topic_code)
        if not prefix:
            continue
        correct, total = buckets.setdefault(prefix, [0, 0])
        total += 1
        if row.is_correct:
            correct += 1
        buckets[prefix] = [correct, total]

    return [
        DomainAggregate(
            domain_prefix=prefix,
            total_questions=total,
            correct=correct,
            cert_tag=cert_n,
        )
        for prefix, (correct, total) in sorted(buckets.items())
    ]


def weak_domains(cert: str | None = None, limit: int = 5) -> list[DomainAggregate]:
    """Domains with the lowest accuracy (weakest first)."""
    domains = [d for d in domain_totals(cert=cert) if d.total_questions > 0]
    domains.sort(key=lambda d: (d.percent, -d.total_questions, d.domain_prefix))
    return domains[: max(0, limit)]


def domain_accuracy_by_version(
    cert: str | None = None,
    exam_version: str | None = None,
) -> list[DomainVersionCell]:
    """Matrix cells: domain prefix × exam_version accuracy from graded answers."""
    cert_n = _normalize_cert(cert)
    with _session() as s:
        q = s.query(UserAnswer).filter(UserAnswer.is_correct.isnot(None))
        if cert_n:
            q = q.filter(UserAnswer.cert_tag == cert_n)
        if exam_version:
            q = q.filter(UserAnswer.exam_version == exam_version)
        rows = q.all()

    buckets: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        prefix = _domain_prefix(row.topic_code)
        if not prefix:
            continue
        version = (row.exam_version or "").strip() or "unknown"
        key = (prefix, version)
        correct, total = buckets.setdefault(key, [0, 0])
        total += 1
        if row.is_correct:
            correct += 1
        buckets[key] = [correct, total]

    return [
        DomainVersionCell(
            domain_prefix=prefix,
            exam_version=version,
            correct=correct,
            total=total,
        )
        for (prefix, version), (correct, total) in sorted(buckets.items())
    ]


def list_exam_versions(cert: str | None = None) -> list[str]:
    """Distinct exam versions seen in graded answers (newest-ish lexical sort)."""
    cert_n = _normalize_cert(cert)
    with _session() as s:
        q = s.query(UserAnswer.exam_version).filter(UserAnswer.is_correct.isnot(None))
        if cert_n:
            q = q.filter(UserAnswer.cert_tag == cert_n)
        versions = {(v or "").strip() or "unknown" for (v,) in q.distinct().all()}
    return sorted(versions)


def domain_trend(
    limit: int = 10,
    cert: str | None = None,
) -> list[DomainTrendPoint]:
    """Recent finished exams with per-domain accuracy (oldest first for charts)."""
    cert_n = _normalize_cert(cert)
    with _session() as s:
        q = (
            s.query(ExamSessionORM)
            .filter(ExamSessionORM.finished_at.isnot(None))
            .order_by(ExamSessionORM.finished_at.desc())
        )
        if cert_n:
            # Prefer sessions whose answers carry the cert tag.
            session_ids = [
                sid
                for (sid,) in s.query(UserAnswer.session_id)
                .filter(UserAnswer.cert_tag == cert_n)
                .distinct()
                .all()
            ]
            if not session_ids:
                return []
            q = q.filter(ExamSessionORM.id.in_(session_ids))
        sessions = q.limit(limit).all()
        out: list[DomainTrendPoint] = []
        for sess in reversed(sessions):
            answers = (
                s.query(UserAnswer)
                .filter(UserAnswer.session_id == sess.id)
                .filter(UserAnswer.is_correct.isnot(None))
                .all()
            )
            buckets: dict[str, list[int]] = {}
            for row in answers:
                if cert_n and row.cert_tag and row.cert_tag != cert_n:
                    continue
                prefix = _domain_prefix(row.topic_code)
                if not prefix:
                    continue
                correct, total = buckets.setdefault(prefix, [0, 0])
                total += 1
                if row.is_correct:
                    correct += 1
                buckets[prefix] = [correct, total]
            domains = {
                prefix: (correct / total if total else 0.0)
                for prefix, (correct, total) in sorted(buckets.items())
            }
            out.append(
                DomainTrendPoint(
                    session_id=sess.id,
                    exam_code=_display_exam_code(sess),
                    exam_version=sess.exam_version or "",
                    finished_at=sess.finished_at,
                    domains=domains,
                )
            )
        return out


def recent_missed_question_ids(limit: int = 20) -> list[str]:
    """Bank question ids missed most recently (unique, newest first)."""
    with _session() as s:
        rows = (
            s.query(UserAnswer.bank_question_id, ExamSessionORM.finished_at)
            .join(ExamSessionORM, UserAnswer.session_id == ExamSessionORM.id)
            .filter(UserAnswer.is_correct.is_(False))
            .filter(UserAnswer.bank_question_id.isnot(None))
            .order_by(ExamSessionORM.finished_at.desc(), UserAnswer.id.desc())
            .all()
        )
    seen: set[str] = set()
    out: list[str] = []
    for qid, _finished in rows:
        if not qid or qid in seen:
            continue
        seen.add(qid)
        out.append(qid)
        if len(out) >= limit:
            break
    return out


def score_trend(limit: int = 20) -> list[ScorePoint]:
    """Recent exam scores, oldest first (convenient for sparkline/charts)."""
    history = exam_history(limit=limit)
    # exam_history is newest-first; reverse for chronological trend.
    return [
        ScorePoint(score=h.score, exam_code=h.exam_code, finished_at=h.finished_at)
        for h in reversed(history)
    ]


def latest_activity() -> dict[str, Any] | None:
    """Most recent finished exam or lab, for Dashboard 'continue' CTA."""
    exams = exam_history(limit=1)
    labs = lab_history(limit=1)
    candidates: list[tuple[float, dict[str, Any]]] = []

    def _ts(when: datetime | None) -> float:
        if when is None:
            return 0.0
        if when.tzinfo is None:
            return when.replace(tzinfo=UTC).timestamp()
        return when.timestamp()

    if exams:
        e = exams[0]
        candidates.append(
            (
                _ts(e.finished_at),
                {
                    "kind": "exam",
                    "exam_code": e.exam_code,
                    "mode": e.mode,
                    "score": e.score,
                    "finished_at": e.finished_at,
                },
            )
        )
    if labs:
        lab = labs[0]
        candidates.append(
            (
                _ts(lab.finished_at),
                {
                    "kind": "lab",
                    "lab_id": lab.lab_id,
                    "score": lab.score,
                    "finished_at": lab.finished_at,
                },
            )
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


# -----/ Practice attempts /-----
@dataclass
class QuestionStat:
    """Aggregated practice history for one bank question id."""

    question_id: str
    seen: int = 0
    misses: int = 0
    last_correct: bool | None = None

    @property
    def unseen(self) -> bool:
        return self.seen == 0

    @property
    def missed(self) -> bool:
        return self.misses > 0


def save_practice_attempt(question_id: str, is_correct: bool) -> int:
    """Persist one Practice library Check. Returns the row id."""
    user = get_or_create_default_user()
    with _session() as s:
        row = PracticeAttempt(
            user_id=user.id,
            question_bank_id=question_id,
            is_correct=is_correct,
            answered_at=datetime.now(UTC),
        )
        s.add(row)
        s.commit()
        return row.id


def question_stats_map() -> dict[str, QuestionStat]:
    """Return per-question practice stats keyed by bank question id."""
    with _session() as s:
        rows = s.query(PracticeAttempt).order_by(PracticeAttempt.answered_at.asc()).all()
        stats: dict[str, QuestionStat] = {}
        for row in rows:
            st = stats.setdefault(
                row.question_bank_id, QuestionStat(question_id=row.question_bank_id)
            )
            st.seen += 1
            if not row.is_correct:
                st.misses += 1
            st.last_correct = row.is_correct
        return stats


def question_history_map() -> dict[str, QuestionStat]:
    """Union of practice attempts and finished-exam answers for custom filters.

    - **seen**: any practice attempt or exam answer for the question
    - **misses**: practice miss or incorrect exam answer
    - **last_correct**: most recent outcome when known (practice preferred if both)
    """
    stats = question_stats_map()
    with _session() as s:
        rows = (
            s.query(UserAnswer.bank_question_id, UserAnswer.is_correct)
            .filter(UserAnswer.bank_question_id.isnot(None))
            .order_by(UserAnswer.id.asc())
            .all()
        )
    for qid, is_correct in rows:
        if not qid:
            continue
        st = stats.setdefault(qid, QuestionStat(question_id=qid))
        st.seen += 1
        if not is_correct:
            st.misses += 1
        st.last_correct = bool(is_correct)
    return stats
