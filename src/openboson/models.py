"""SQLAlchemy ORM models for OpenBoson persistence.

Schema overview:
    users           - local profiles (auto-created on first launch).
    exams           - registered exam metadata (CCNA 200-301 v1.1, etc.).
    questions       - authored questions belonging to an exam.
    exam_sessions   - one run of an exam by a user.
    user_answers    - a single user's answer within an exam session.
    lab_sessions    - one run of a guided lab.
    lab_step        - result of one lab task within a lab session.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, Integer, Boolean, DateTime, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Default")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    exam_sessions: Mapped[list["ExamSession"]] = relationship(back_populates="user")
    lab_sessions: Mapped[list["LabSession"]] = relationship(back_populates="user")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    exam_code: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[str] = mapped_column(String(20), default="v1.1")
    provider: Mapped[str] = mapped_column(String(60), default="openboson")
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    exam_sessions: Mapped[list["ExamSession"]] = relationship(back_populates="exam")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    topic_code: Mapped[str] = mapped_column(String(20), index=True)
    type: Mapped[str] = mapped_column(String(30))
    stem_json: Mapped[str] = mapped_column(Text)
    choices_json: Mapped[str] = mapped_column(Text, default="[]")
    correct_answer_json: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    exam: Mapped["Exam"] = relationship(back_populates="questions")


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    exam_id: Mapped[int | None] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=True
    )
    # Stable attempt identity (survives missing Exam rows / bundled banks).
    exam_code: Mapped[str] = mapped_column(String(40), default="", index=True)
    exam_version: Mapped[str] = mapped_column(String(20), default="")
    mode: Mapped[str] = mapped_column(String(20), default="exam")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    user: Mapped["User"] = relationship(back_populates="exam_sessions")
    exam: Mapped["Exam"] = relationship(back_populates="exam_sessions")
    answers: Mapped[list["UserAnswer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"))
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=True
    )
    # Bank YAML question id (stable across runs; ORM question rows are optional).
    bank_question_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    answer_json: Mapped[str] = mapped_column(Text, default="[]")
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped["ExamSession"] = relationship(back_populates="answers")


class LabSession(Base):
    __tablename__ = "lab_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    lab_id: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="lab_sessions")
    steps: Mapped[list["LabStep"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class LabStep(Base):
    __tablename__ = "lab_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_session_id: Mapped[int] = mapped_column(ForeignKey("lab_sessions.id", ondelete="CASCADE"))
    step_index: Mapped[int] = mapped_column(Integer)
    expected_config: Mapped[str] = mapped_column(Text, default="")
    submitted_config: Mapped[str] = mapped_column(Text, default="")
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["LabSession"] = relationship(back_populates="steps")


class PracticeAttempt(Base):
    """A single Check from the Practice library (not a full exam)."""

    __tablename__ = "practice_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_bank_id: Mapped[str] = mapped_column(String(80), index=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
