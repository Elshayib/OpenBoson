"""Exam session state machine.

A session is a single in-progress attempt. Questions may come from a full
bank or a blueprint-sampled subset. Grading is delegated to
``openboson.exsim.scoring``.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from openboson.bank_schema import ExamBank, Question, QuestionType, Topic
from openboson.exsim.blueprint import InsufficientPoolError


class ExamMode(StrEnum):
    PRACTICE = "practice"  # immediate feedback (single-question Check)
    EXAM = "exam"  # scored at end; no feedback while answering


class SessionStatus(StrEnum):
    """Lifecycle of a persisted exam attempt."""

    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    FINISHED = "finished"
    ABANDONED = "abandoned"


SNAPSHOT_VERSION = 1


def presentation_from_dict(data: dict[str, Any] | None) -> QuestionPresentation:
    """Rebuild a :class:`QuestionPresentation` from ``to_dict()`` output."""
    if not data:
        return QuestionPresentation()
    left_raw = data.get("left_items")
    right_raw = data.get("right_items")
    drag_left = None
    drag_right = None
    if left_raw:
        drag_left = [
            DragItem(id=str(item["id"]), text=str(item["text"]))
            if isinstance(item, dict)
            else DragItem(id=f"L{i}", text=str(item))
            for i, item in enumerate(left_raw)
        ]
    if right_raw:
        drag_right = [
            DragItem(id=str(item["id"]), text=str(item["text"]))
            if isinstance(item, dict)
            else DragItem(id=f"R{i}", text=str(item))
            for i, item in enumerate(right_raw)
        ]
    return QuestionPresentation(
        choice_ids=list(data["choice_ids"]) if data.get("choice_ids") is not None else None,
        ordered_items=(
            list(data["ordered_items"]) if data.get("ordered_items") is not None else None
        ),
        drag_left=drag_left,
        drag_right=drag_right,
    )


@dataclass
class DragItem:
    """Opaque display token for one side of a drag-match question."""

    id: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "text": self.text}


@dataclass
class QuestionPresentation:
    """Stable per-session display order for one question.

    Grading always uses opaque choice IDs / semantic text values from the
    authored question — never display positions.
    """

    choice_ids: list[str] | None = None
    ordered_items: list[str] | None = None
    drag_left: list[DragItem] | None = None
    drag_right: list[DragItem] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API / QuestionCard (dict-shaped presentation).

        Public keys: ``choice_ids``, ``ordered_items``, ``left_items``,
        ``right_items``. Internal dataclass fields remain ``drag_left`` /
        ``drag_right``; clients must not depend on those names in the dict.
        """
        out: dict[str, Any] = {}
        if self.choice_ids is not None:
            out["choice_ids"] = list(self.choice_ids)
        if self.ordered_items is not None:
            out["ordered_items"] = list(self.ordered_items)
        if self.drag_left is not None:
            out["left_items"] = [d.to_dict() for d in self.drag_left]
        if self.drag_right is not None:
            out["right_items"] = [d.to_dict() for d in self.drag_right]
        return out


@dataclass
class UserAnswer:
    """A user's answer for one question within a session."""

    question_id: str
    answer: dict[str, Any] | list[Any] | str | None = None
    is_correct: bool | None = None
    time_spent_seconds: float = 0.0
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExamSession:
    """Mutable in-progress exam attempt."""

    session_id: str
    exam: ExamBank
    mode: ExamMode = ExamMode.EXAM
    questions: list[Question] = field(default_factory=list)
    current_index: int = 0
    answers: dict[str, UserAnswer] = field(default_factory=dict)
    bookmarked: set[str] = field(default_factory=set)
    marked_for_review: set[str] = field(default_factory=set)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    blueprint_id: str | None = None
    presentation: dict[str, QuestionPresentation] = field(default_factory=dict)
    status: SessionStatus = SessionStatus.IN_PROGRESS
    remaining_seconds: int | None = None
    paused_at: datetime | None = None
    _shuffle_on_init: bool = True

    @classmethod
    def create(
        cls,
        exam: ExamBank,
        mode: ExamMode = ExamMode.EXAM,
        *,
        shuffle: bool = True,
        blueprint_id: str | None = None,
        questions: list[Question] | None = None,
        rng: random.Random | None = None,
        seed: int | None = None,
    ) -> ExamSession:
        """Create a session.

        ``questions=None`` uses the full bank (optionally shuffled).
        An explicit empty list is rejected — it must never expand to the full bank.
        """
        if rng is None:
            rng = random.Random(seed) if seed is not None else random.Random()

        if questions is not None:
            if not questions:
                raise InsufficientPoolError("Cannot start an exam with an empty question set")
            qs = list(questions)
        else:
            qs = list(exam.questions)
            if not qs:
                raise InsufficientPoolError("Exam bank has no questions")
            if shuffle:
                rng.shuffle(qs)

        remaining: int | None = None
        if exam.time_limit_minutes and exam.time_limit_minutes > 0:
            remaining = int(exam.time_limit_minutes) * 60

        session = cls(
            session_id=uuid.uuid4().hex,
            exam=exam,
            mode=mode,
            questions=qs,
            blueprint_id=blueprint_id,
            remaining_seconds=remaining,
            _shuffle_on_init=False,
        )
        session.presentation = {q.id: build_question_presentation(q, rng) for q in qs}
        return session

    def presentation_for(self, question_id: str) -> QuestionPresentation | None:
        return self.presentation.get(question_id)

    def reshuffle_presentation(
        self,
        question_id: str,
        *,
        rng: random.Random | None = None,
    ) -> QuestionPresentation:
        """Build a fresh presentation (practice may reshuffle on each open)."""
        question = next(q for q in self.questions if q.id == question_id)
        pres = build_question_presentation(question, rng or random.Random())
        self.presentation[question_id] = pres
        return pres

    @property
    def current_question(self) -> Question:
        if not self.questions:
            raise RuntimeError("session has no questions")
        if self.current_index < 0 or self.current_index >= len(self.questions):
            raise IndexError("current_index out of range")
        return self.questions[self.current_index]

    def submit_answer(
        self,
        question_id: str,
        answer: dict[str, Any] | list[Any] | str | None,
        time_spent_seconds: float = 0.0,
        *,
        grade_now: bool = False,
    ) -> bool | None:
        """Record a user's answer.

        In ``practice`` mode (or when ``grade_now`` is True), immediately grade
        and return correctness. In ``exam`` mode, just record and return ``None``.
        """
        user_ans = UserAnswer(
            question_id=question_id,
            answer=answer,
            time_spent_seconds=time_spent_seconds,
        )
        self.answers[question_id] = user_ans
        if grade_now or self.mode == ExamMode.PRACTICE:
            from openboson.exsim.scoring import grade_answer

            question = next(q for q in self.questions if q.id == question_id)
            user_ans.is_correct = grade_answer(question, answer)
            return user_ans.is_correct
        return None

    def toggle_bookmark(self, question_id: str) -> bool:
        """Toggle bookmark. Returns the new bookmark state."""
        if question_id in self.bookmarked:
            self.bookmarked.discard(question_id)
            return False
        self.bookmarked.add(question_id)
        return True

    def toggle_mark_for_review(self, question_id: str) -> bool:
        if question_id in self.marked_for_review:
            self.marked_for_review.discard(question_id)
            return False
        self.marked_for_review.add(question_id)
        return True

    def next(self) -> Question | None:
        """Move to the next question. Returns None if at end."""
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            return self.current_question
        return None

    def previous(self) -> Question | None:
        if self.current_index > 0:
            self.current_index -= 1
            return self.current_question
        return None

    def goto(self, index: int) -> Question:
        if 0 <= index < len(self.questions):
            self.current_index = index
            return self.current_question
        raise IndexError(index)

    def is_finished(self) -> bool:
        return self.finished_at is not None or self.status == SessionStatus.FINISHED

    def is_paused(self) -> bool:
        return self.status == SessionStatus.PAUSED

    def is_resumable(self) -> bool:
        return (
            self.status
            in (
                SessionStatus.IN_PROGRESS,
                SessionStatus.PAUSED,
            )
            and not self.is_finished()
        )

    def pause(self, remaining_seconds: int | None = None) -> None:
        """Freeze the attempt; optional remaining overrides the stored countdown."""
        if self.is_finished():
            raise RuntimeError("Cannot pause a finished session")
        if remaining_seconds is not None:
            self.remaining_seconds = max(0, int(remaining_seconds))
        self.status = SessionStatus.PAUSED
        self.paused_at = datetime.now(UTC)

    def resume(self) -> None:
        """Unfreeze a paused attempt. Remaining time is unchanged."""
        if self.is_finished():
            raise RuntimeError("Cannot resume a finished session")
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.IN_PROGRESS
            self.paused_at = None

    def finish(self) -> datetime:
        self.finished_at = datetime.now(UTC)
        self.status = SessionStatus.FINISHED
        self.paused_at = None
        return self.finished_at

    def answered_count(self) -> int:
        return sum(1 for a in self.answers.values() if a.answer is not None)

    def to_snapshot(self) -> dict[str, Any]:
        """Serialize attempt state for SQLite / restart restore."""
        answers: dict[str, Any] = {}
        for qid, ua in self.answers.items():
            answers[qid] = {
                "answer": ua.answer,
                "is_correct": ua.is_correct,
                "time_spent_seconds": ua.time_spent_seconds,
                "submitted_at": ua.submitted_at.isoformat() if ua.submitted_at else None,
            }
        presentation = {qid: pres.to_dict() for qid, pres in self.presentation.items()}
        return {
            "version": SNAPSHOT_VERSION,
            "session_id": self.session_id,
            "mode": str(self.mode),
            "status": str(self.status),
            "blueprint_id": self.blueprint_id,
            "exam_code": self.exam.code,
            "exam_version": self.exam.version,
            "exam_title": self.exam.title,
            "exam_provider": self.exam.provider,
            "time_limit_minutes": self.exam.time_limit_minutes,
            "question_ids": [q.id for q in self.questions],
            "current_index": self.current_index,
            "bookmarked": sorted(self.bookmarked),
            "marked_for_review": sorted(self.marked_for_review),
            "presentation": presentation,
            "answers": answers,
            "remaining_seconds": self.remaining_seconds,
            "started_at": self.started_at.isoformat(),
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    @classmethod
    def from_snapshot(
        cls,
        data: dict[str, Any],
        questions_by_id: dict[str, Question],
        *,
        exam: ExamBank | None = None,
    ) -> ExamSession:
        """Rebuild a session from ``to_snapshot()`` output.

        Missing question ids raise ``KeyError``.
        """
        qids = list(data.get("question_ids") or [])
        missing = [qid for qid in qids if qid not in questions_by_id]
        if missing:
            raise KeyError(f"Snapshot references missing questions: {missing[:5]}")
        qs = [questions_by_id[qid] for qid in qids]
        if not qs:
            raise InsufficientPoolError("Cannot restore an exam with an empty question set")

        if exam is None:
            topic_codes = sorted({q.topic_code for q in qs if q.topic_code})
            topics = [Topic(code=code, name=f"Topic {code}", weight=0.0) for code in topic_codes]
            if not topics:
                topics = [Topic(code="1.0", name="General", weight=1.0)]
            limit = int(data.get("time_limit_minutes") or 120)
            exam = ExamBank(
                title=str(data.get("exam_title") or "Restored exam"),
                code=str(data.get("exam_code") or "unknown"),
                version=str(data.get("exam_version") or "v1.1"),
                provider=str(data.get("exam_provider") or "openboson"),
                description="",
                topics=topics,
                questions=qs,
                time_limit_minutes=max(1, limit),
            )
        else:
            # Prefer snapshot question order; keep exam metadata.
            exam = exam.model_copy(update={"questions": qs})

        mode = ExamMode(str(data.get("mode") or ExamMode.EXAM))
        status = SessionStatus(str(data.get("status") or SessionStatus.IN_PROGRESS))
        started = _parse_dt(data.get("started_at")) or datetime.now(UTC)
        paused = _parse_dt(data.get("paused_at"))
        finished = _parse_dt(data.get("finished_at"))

        session = cls(
            session_id=str(data.get("session_id") or uuid.uuid4().hex),
            exam=exam,
            mode=mode,
            questions=qs,
            current_index=int(data.get("current_index") or 0),
            bookmarked=set(data.get("bookmarked") or []),
            marked_for_review=set(data.get("marked_for_review") or []),
            started_at=started,
            finished_at=finished,
            blueprint_id=data.get("blueprint_id"),
            status=status,
            remaining_seconds=(
                int(data["remaining_seconds"])
                if data.get("remaining_seconds") is not None
                else None
            ),
            paused_at=paused,
            _shuffle_on_init=False,
        )
        raw_pres = data.get("presentation") or {}
        session.presentation = {qid: presentation_from_dict(raw_pres.get(qid)) for qid in qids}
        for qid, raw in (data.get("answers") or {}).items():
            if not isinstance(raw, dict):
                continue
            submitted = _parse_dt(raw.get("submitted_at")) or started
            session.answers[qid] = UserAnswer(
                question_id=qid,
                answer=raw.get("answer"),
                is_correct=raw.get("is_correct"),
                time_spent_seconds=float(raw.get("time_spent_seconds") or 0.0),
                submitted_at=submitted,
            )
        # Clamp index after restore.
        if session.current_index < 0 or session.current_index >= len(qs):
            session.current_index = 0
        return session


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def build_question_presentation(
    question: Question,
    rng: random.Random | None = None,
) -> QuestionPresentation:
    """Build a randomized presentation order for ``question``."""
    rng = rng or random.Random()
    if question.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
        ids = [c.id for c in (question.choices or [])]
        rng.shuffle(ids)
        return QuestionPresentation(choice_ids=ids)

    if question.type == QuestionType.ORDERED_LIST:
        items = list(question.ordered_items or [])
        rng.shuffle(items)
        return QuestionPresentation(ordered_items=items)

    if question.type == QuestionType.DRAG_MATCH:
        pairs = list(question.drag_pairs or [])
        left = [DragItem(id=f"L{i}", text=p.left) for i, p in enumerate(pairs)]
        right = [DragItem(id=f"R{i}", text=p.right) for i, p in enumerate(pairs)]
        rng.shuffle(left)
        rng.shuffle(right)
        return QuestionPresentation(drag_left=left, drag_right=right)

    return QuestionPresentation()
