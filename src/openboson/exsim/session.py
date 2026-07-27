"""Exam session state machine.

A session is a single in-progress attempt at an exam bank. The session
keeps a shuffled copy of the questions, tracks the current index, the
user's submitted answers, and bookmarks. Grading is delegated to
``openboson.exsim.scoring``.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from openboson.bank_schema import ExamBank, Question, QuestionType


class ExamMode(str, Enum):
    STUDY = "study"  # immediate feedback per question
    TIMED = "timed"  # scored at end; timer in GUI
    CUSTOM = "custom"  # user-selected topic filters


@dataclass
class UserAnswer:
    """A user's answer for one question within a session."""

    question_id: str
    answer: dict[str, Any] | list[Any] | str | None = None
    is_correct: bool | None = None
    time_spent_seconds: float = 0.0
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExamSession:
    """Mutable in-progress exam attempt."""

    session_id: str
    exam: ExamBank
    mode: ExamMode = ExamMode.TIMED
    questions: list[Question] = field(default_factory=list)
    current_index: int = 0
    answers: dict[str, UserAnswer] = field(default_factory=dict)
    bookmarked: set[str] = field(default_factory=set)
    marked_for_review: set[str] = field(default_factory=set)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        # Copy questions from the exam and shuffle for a fresh attempt.
        self.questions = list(self.exam.questions)
        random.shuffle(self.questions)

    @classmethod
    def create(cls, exam: ExamBank, mode: ExamMode = ExamMode.TIMED) -> "ExamSession":
        return cls(
            session_id=uuid.uuid4().hex,
            exam=exam,
            mode=mode,
        )

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
        study_mode_grade: bool = False,
    ) -> bool | None:
        """Record a user's answer.

        In ``study`` mode, immediately grade and return correctness.
        In ``timed`` mode, just record and return ``None``.
        """
        user_ans = UserAnswer(
            question_id=question_id,
            answer=answer,
            time_spent_seconds=time_spent_seconds,
        )
        self.answers[question_id] = user_ans
        if study_mode_grade or self.mode == ExamMode.STUDY:
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
        self.finished_at = datetime.now(timezone.utc)
        return self.finished_at

    def answered_count(self) -> int:
        return sum(
            1 for a in self.answers.values() if a.answer is not None
        )
