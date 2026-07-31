"""Pydantic v2 schemas for question banks.

This is the canonical definition of what a valid OpenBoson question bank looks
like. The companion ``bank_loader`` module loads YAML into these models.

Question ``type`` values:
    - ``single_choice``  : one correct answer (radio buttons)
    - ``multiple_choice``: any number of correct answers (checkboxes)
    - ``drag_match``     : left/right pairs must be matched
    - ``ordered_list``   : items must be placed in correct order
    - ``sim``            : performance-based placeholder (CLI/topology)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


CertTag = Literal["ccna", "ccnp"]


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    DRAG_MATCH = "drag_match"
    ORDERED_LIST = "ordered_list"
    SIM = "sim"


class Choice(BaseModel):
    """A single answer choice for single/multiple-choice questions."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    media_url: str | None = None
    rationale: str | None = None  # why this choice is right or wrong


class DragPair(BaseModel):
    """One pair for a drag-and-drop matching question."""

    model_config = ConfigDict(extra="forbid")

    left: str
    right: str


class SimSpec(BaseModel):
    """Placeholder for performance-based questions.

    The real sim engine is Phase 2; for MVP we store instructions and context
    that the GUI renders as a placeholder.
    """

    model_config = ConfigDict(extra="forbid")

    instructions: str
    topology_ref: str | None = None
    expected_output: str | None = None


class SingleChoiceAnswer(BaseModel):
    """``correct`` payload for ``single_choice`` questions."""

    model_config = ConfigDict(extra="forbid")

    answer: str  # choice id


class MultipleChoiceAnswer(BaseModel):
    """``correct`` payload for ``multiple_choice`` questions."""

    model_config = ConfigDict(extra="forbid")

    answers: list[str]  # choice ids
    partial_credit: bool = False


class DragMatchAnswer(BaseModel):
    """``correct`` payload for ``drag_match`` questions."""

    model_config = ConfigDict(extra="forbid")

    pairs: list[DragPair]


class OrderedListAnswer(BaseModel):
    """``correct`` payload for ``ordered_list`` questions."""

    model_config = ConfigDict(extra="forbid")

    order: list[str]  # item ids


class SimAnswer(BaseModel):
    """``correct`` payload for ``sim`` questions (graded manually or by Phase 2)."""

    model_config = ConfigDict(extra="forbid")

    expected_config: str | None = None
    expected_commands: list[str] | None = None
    instructions: str | None = None  # optional human instructions surfaced to grader


class Topic(BaseModel):
    """A topic code that the bank covers (e.g. ``1.0 Network Fundamentals``)."""

    model_config = ConfigDict(extra="forbid")

    code: str  # e.g. "1.1"
    name: str  # e.g. "Network Fundamentals"
    weight: float = Field(default=0.0, description="Domain weight, e.g. 0.20 for 20%.")


class Question(BaseModel):
    """A single question in an exam bank / question pool."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: QuestionType
    topic_code: str  # e.g. "1.1"
    difficulty: int = Field(default=3, ge=1, le=5)
    cert_tags: list[CertTag] = Field(min_length=1)
    stem: str  # question text (Markdown supported by GUI)
    media_url: str | None = None
    choices: list[Choice] | None = None  # for single/multiple choice
    drag_pairs: list[DragPair] | None = None  # left/right for drag_match display
    ordered_items: list[str] | None = None  # shuffled display items for ordered_list
    sim: SimSpec | None = None  # for sim
    correct: dict[str, Any]  # raw payload, validated per type in ``validate_correct``
    explanation: str | None = None
    references: list[str] | None = None

    @field_validator("cert_tags")
    @classmethod
    def _unique_cert_tags(cls, value: list[CertTag]) -> list[CertTag]:
        if not value:
            raise ValueError("cert_tags must not be empty")
        # Preserve order while deduping.
        seen: set[str] = set()
        out: list[CertTag] = []
        for tag in value:
            if tag not in seen:
                seen.add(tag)
                out.append(tag)
        return out

    @field_validator("correct")
    @classmethod
    def _validate_correct(cls, value: dict[str, Any]) -> dict[str, Any]:
        # The actual model validation happens lazily via ``correct_answer_model``
        # so we keep the raw dict but sanity-check keys exist.
        if not value:
            raise ValueError("correct payload must not be empty")
        return value

    @property
    def correct_answer_model(self) -> Union[
        SingleChoiceAnswer,
        MultipleChoiceAnswer,
        DragMatchAnswer,
        OrderedListAnswer,
        SimAnswer,
    ]:
        """Return the strongly-typed correct answer for this question type."""
        mapping: dict[QuestionType, type[BaseModel]] = {
            QuestionType.SINGLE_CHOICE: SingleChoiceAnswer,
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceAnswer,
            QuestionType.DRAG_MATCH: DragMatchAnswer,
            QuestionType.ORDERED_LIST: OrderedListAnswer,
            QuestionType.SIM: SimAnswer,
        }
        model_cls = mapping[self.type]
        return model_cls.model_validate(self.correct)  # type: ignore[return-value]

    def matches_cert(self, cert: CertTag) -> bool:
        return cert in self.cert_tags


class ExamBank(BaseModel):
    """A complete exam question bank / pool file."""

    model_config = ConfigDict(extra="forbid")

    title: str
    code: str  # e.g. "200-301" or pool id
    version: str = "v1.1"
    provider: str = "openboson"
    description: str | None = None
    topics: list[Topic]
    pass_score: float = Field(default=0.825, ge=0.0, le=1.0)
    time_limit_minutes: int = Field(default=120, ge=1)
    questions: list[Question]

    @field_validator("questions")
    @classmethod
    def _questions_not_empty(cls, value: list[Question]) -> list[Question]:
        if not value:
            raise ValueError("questions list must not be empty")
        return value

    @property
    def topic_codes(self) -> set[str]:
        return {t.code for t in self.topics}

    def domain_weight(self, topic_code_prefix: str) -> float:
        """Return the cumulative weight of all topics matching prefix.

        ``prefix`` like ``"1."`` matches ``1.1``, ``1.2``, ``1.3``, etc.
        """
        total = 0.0
        for t in self.topics:
            if t.code.startswith(topic_code_prefix.rstrip(".")):
                total += t.weight
        return total


class QuestionPool(BaseModel):
    """Merged question pool across one or more bank YAML files."""

    model_config = ConfigDict(extra="forbid")

    questions: list[Question] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    source_codes: list[str] = Field(default_factory=list)

    def by_id(self) -> dict[str, Question]:
        return {q.id: q for q in self.questions}
