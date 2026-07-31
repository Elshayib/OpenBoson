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

from openboson.bank_schema import ExamBank, Question, QuestionType
from openboson.exsim.blueprint import InsufficientPoolError


class ExamMode(StrEnum):
    PRACTICE = "practice"  # immediate feedback (single-question Check)
    EXAM = "exam"  # scored at end; no feedback while answering


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

        session = cls(
            session_id=uuid.uuid4().hex,
            exam=exam,
            mode=mode,
            questions=qs,
            blueprint_id=blueprint_id,
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
        return self.finished_at is not None

    def finish(self) -> datetime:
        self.finished_at = datetime.now(UTC)
        return self.finished_at

    def answered_count(self) -> int:
        return sum(1 for a in self.answers.values() if a.answer is not None)


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
