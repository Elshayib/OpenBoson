"""Custom exam builder: filter the pool and sample a fixed-length attempt.

Unlike official blueprints (fixed domain weights), custom exams use free-form
filters (cert, topics, difficulty, missed/unseen) plus length, time, and seed.
"""

from __future__ import annotations

import random
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from openboson.bank_schema import CertTag, ExamBank, Question, Topic
from openboson.exsim.blueprint import InsufficientPoolError

HistoryFilter = Literal["any", "missed", "unseen"]


def _history_counts(st: Any) -> tuple[int, int]:
    """Return ``(seen, misses)`` from a QuestionStat-like object or mapping."""
    if st is None:
        return 0, 0
    if isinstance(st, dict):
        return int(st.get("seen") or 0), int(st.get("misses") or 0)
    return int(getattr(st, "seen", 0) or 0), int(getattr(st, "misses", 0) or 0)


class CustomExamSpec(BaseModel):
    """Runtime filter + sampling request (also the body of a saved preset)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    title: str = "Custom Exam"
    cert: CertTag
    topic_codes: list[str] = Field(default_factory=list)
    difficulties: list[int] = Field(default_factory=list)
    history: HistoryFilter = "any"
    question_count: int = Field(default=40, ge=1, le=200)
    time_limit_minutes: int = Field(default=60, ge=0, le=480)
    seed: int | None = None
    pass_score: float = Field(default=0.825, ge=0.0, le=1.0)

    @field_validator("topic_codes", mode="before")
    @classmethod
    def _normalize_topics(cls, value: Any) -> list[str]:
        if not value:
            return []
        return [str(t).strip() for t in value if str(t).strip()]

    @field_validator("difficulties", mode="before")
    @classmethod
    def _normalize_difficulties(cls, value: Any) -> list[int]:
        if not value:
            return []
        out: list[int] = []
        for item in value:
            n = int(item)
            if 1 <= n <= 5 and n not in out:
                out.append(n)
        return out


def _topic_matches(question: Question, topic_codes: list[str]) -> bool:
    """Match exact topic codes or domain prefixes (e.g. ``3`` / ``3.``)."""
    if not topic_codes:
        return True
    code = (question.topic_code or "").strip()
    if not code:
        return False
    for raw in topic_codes:
        needle = raw.rstrip(".")
        if not needle:
            continue
        if code in (raw, needle):
            return True
        if code.startswith(needle + "."):
            return True
    return False


def filter_questions(
    pool_questions: list[Question],
    spec: CustomExamSpec,
    *,
    history: dict[str, Any] | None = None,
) -> list[Question]:
    """Return questions matching ``spec`` filters (order preserved).

    ``history`` maps question id → object with ``seen`` / ``misses`` (or a
    mapping with those keys). Used when ``spec.history`` is missed/unseen.
    """
    hist = history or {}
    eligible: list[Question] = []
    for q in pool_questions:
        if not q.matches_cert(spec.cert):
            continue
        if not _topic_matches(q, spec.topic_codes):
            continue
        if spec.difficulties and int(q.difficulty) not in spec.difficulties:
            continue
        if spec.history != "any":
            seen, misses = _history_counts(hist.get(q.id))
            if spec.history == "missed" and misses <= 0:
                continue
            if spec.history == "unseen" and seen > 0:
                continue
        eligible.append(q)
    return eligible


def coverage_for_custom(
    pool_questions: list[Question],
    spec: CustomExamSpec,
    *,
    history: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Return ``{"eligible": N, "requested": M}`` for builder preview."""
    eligible = filter_questions(pool_questions, spec, history=history)
    return {"eligible": len(eligible), "requested": spec.question_count}


def build_exam_from_custom(
    pool_questions: list[Question],
    spec: CustomExamSpec,
    *,
    history: dict[str, Any] | None = None,
    rng: random.Random | None = None,
) -> list[Question]:
    """Sample ``spec.question_count`` questions without replacement.

    Raises :class:`InsufficientPoolError` when the filtered pool is too small.
    """
    eligible = filter_questions(pool_questions, spec, history=history)
    need = spec.question_count
    if len(eligible) < need:
        raise InsufficientPoolError(
            (
                f"Not enough questions for custom exam ({spec.title}): "
                f"need {need}, have {len(eligible)}"
            ),
            deficits={"pool": need - len(eligible)},
        )
    if rng is None:
        rng = random.Random(spec.seed) if spec.seed is not None else random.Random()
    pool = list(eligible)
    rng.shuffle(pool)
    return pool[:need]


def bank_from_custom(spec: CustomExamSpec, questions: list[Question]) -> ExamBank:
    """Wrap sampled questions in an ``ExamBank`` for session/scoring."""
    topic_codes = sorted({q.topic_code for q in questions if q.topic_code})
    if not topic_codes:
        topics = [Topic(code="1.0", name="General", weight=1.0)]
    else:
        weight = 1.0 / len(topic_codes)
        topics = [Topic(code=code, name=f"Topic {code}", weight=weight) for code in topic_codes]
    return ExamBank(
        title=spec.title,
        code="custom",
        version="custom",
        provider="openboson",
        description="Custom exam",
        cert_tags=[spec.cert],
        topics=topics,
        pass_score=spec.pass_score,
        time_limit_minutes=spec.time_limit_minutes,
        questions=questions,
    )
