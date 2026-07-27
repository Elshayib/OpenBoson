"""Exam session scoring.

Pure functions that grade individual answers and roll up scores across an
exam session, including per-domain breakdown.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from openboson.bank_schema import (
    DragMatchAnswer,
    ExamBank,
    MultipleChoiceAnswer,
    OrderedListAnswer,
    Question,
    QuestionType,
    SimAnswer,
    SingleChoiceAnswer,
)
from openboson.exsim.session import ExamSession, UserAnswer


@dataclass
class DomainBreakdown:
    domain_prefix: str  # e.g. "1." for 1.0 Network Fundamentals
    total: int = 0
    correct: int = 0
    weight: float = 0.0  # from the exam bank topics

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return self.correct / self.total

    @property
    def weighted_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return self.percent * self.weight


@dataclass
class ExamResult:
    session_id: str
    exam_code: str
    exam_version: str
    mode: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    score: float  # 0.0 - 1.0
    passing_score: float
    passed: bool
    domain_breakdown: dict[str, DomainBreakdown] = field(default_factory=dict)
    question_results: dict[str, bool] = field(default_factory=dict)

    @property
    def score_percent(self) -> float:
        return self.score * 100.0


def grade_answer(question: Question, user_answer: Any) -> bool:
    """Grade a single answer given a question and the user's submitted answer.

    ``user_answer`` is a dict (raw) conforming to the expected answer shape.
    """
    if user_answer is None:
        return False
    correct = question.correct_answer_model
    if question.type == QuestionType.SINGLE_CHOICE:
        assert isinstance(correct, SingleChoiceAnswer)
        return _grade_single_choice(correct, user_answer)
    if question.type == QuestionType.MULTIPLE_CHOICE:
        assert isinstance(correct, MultipleChoiceAnswer)
        return _grade_multiple_choice(correct, user_answer)
    if question.type == QuestionType.DRAG_MATCH:
        assert isinstance(correct, DragMatchAnswer)
        return _grade_drag_match(correct, user_answer)
    if question.type == QuestionType.ORDERED_LIST:
        assert isinstance(correct, OrderedListAnswer)
        return _grade_ordered_list(correct, user_answer)
    if question.type == QuestionType.SIM:
        assert isinstance(correct, SimAnswer)
        return _grade_sim(correct, user_answer)
    raise ValueError(f"Unknown question type: {question.type}")


def _grade_single_choice(correct: SingleChoiceAnswer, user_answer: Any) -> bool:
    if isinstance(user_answer, dict):
        return str(user_answer.get("answer", "")) == correct.answer
    if isinstance(user_answer, str):
        return user_answer == correct.answer
    return False


def _grade_multiple_choice(correct: MultipleChoiceAnswer, user_answer: Any) -> bool:
    user_ids: set[str]
    if isinstance(user_answer, dict):
        user_ids = set(user_answer.get("answers", []))
    elif isinstance(user_answer, (list, tuple)):
        user_ids = set(user_answer)
    elif isinstance(user_answer, str):
        user_ids = {user_answer}
    else:
        return False

    correct_id_set = set(correct.answers)
    if correct.partial_credit:
        # Partial credit: the score ratio; but grade_answer is boolean.
        # We require at least all correct answers and no wrong answers; if
        # that's not achievable with partial_credit, fall back to exact match.
        return user_ids == correct_id_set
    return user_ids == correct_id_set


def _grade_drag_match(correct: DragMatchAnswer, user_answer: Any) -> bool:
    """Pairs must match exactly (case-sensitive). The order of pairs may vary
    because the user pairs them up; order across pairs is not significant."""
    if isinstance(user_answer, dict) and "pairs" in user_answer:
        pairs = user_answer["pairs"]
    elif isinstance(user_answer, list):
        pairs = user_answer
    else:
        return False

    expected = {(p.left, p.right) for p in correct.pairs}
    try:
        submitted = {(p["left"], p["right"]) for p in pairs}
    except (KeyError, TypeError):
        try:
            submitted = {(p.left, p.right) for p in pairs}
        except AttributeError:
            return False
    return submitted == expected


def _grade_ordered_list(correct: OrderedListAnswer, user_answer: Any) -> bool:
    if isinstance(user_answer, dict) and "order" in user_answer:
        ordered = user_answer["order"]
    elif isinstance(user_answer, list):
        ordered = user_answer
    else:
        return False
    return list(ordered) == list(correct.order)


def _grade_sim(correct: SimAnswer, user_answer: Any) -> bool:
    # Phase 2 will grade these via the netsim grader; for MVP we accept the
    # submitted config as correct only if it contains all expected_commands.
    expected_cmds = correct.expected_commands or []
    if not expected_cmds:
        return False
    if isinstance(user_answer, dict):
        submitted_text = user_answer.get("config") or user_answer.get("submitted_config") or ""
    else:
        submitted_text = str(user_answer)
    submitted_lines = {line.strip() for line in submitted_text.splitlines() if line.strip()}
    return all(cmd.strip() in submitted_lines for cmd in expected_cmds)


def score_exam(session: ExamSession) -> ExamResult:
    """Score a finished session. Grades all answers, computes per-domain
    breakdown, and determines a pass/fail against the bank's pass_score."""
    # Grade any answers not yet graded (timed mode submits without grading).
    for question in session.questions:
        user_ans: UserAnswer | None = session.answers.get(question.id)
        if user_ans is None:
            continue
        if user_ans.is_correct is None:
            user_ans.is_correct = grade_answer(question, user_ans.answer)

    # Build per-domain breakdown using first-segment prefixes (1,2,3,4,5,6).
    bank = session.exam
    # Pre-collect weights per first-segment domain (e.g. "1.").
    # Strategy: prefer the domain-summary entry "X.0" (which carries the
    # full domain weight per the CCNA blueprint). If no "X.0" entry is
    # present, fall back to summing the subtopic entries whose second
    # segment is non-zero.
    domain_weights: dict[str, float] = {}
    domain_has_rollup: set[str] = set()
    for topic in bank.topics:
        parts = topic.code.split(".")
        prefix = parts[0] + "."
        if len(parts) >= 2 and parts[1] == "0":
            # Domain rollup entry; its weight is the full domain weight.
            domain_weights[prefix] = (
                domain_weights.get(prefix, 0.0) + topic.weight
            )
            domain_has_rollup.add(prefix)
        # Subtopic weights are tracked separately (not rolled up) to avoid
        # double-counting against the rollup.
    # For any domains without a rollup, sum their subtopic weights.
    subtopic_sums: dict[str, float] = {}
    for topic in bank.topics:
        parts = topic.code.split(".")
        if len(parts) < 2 or parts[1] == "0":
            continue
        prefix = parts[0] + "."
        subtopic_sums[prefix] = subtopic_sums.get(prefix, 0.0) + topic.weight
    for prefix, sub_sum in subtopic_sums.items():
        if prefix not in domain_has_rollup:
            domain_weights[prefix] = domain_weights.get(prefix, 0.0) + sub_sum
    breakdown: dict[str, DomainBreakdown] = {}
    # Pre-create domain entries from any topic present in the bank.
    for prefix, weight in domain_weights.items():
        breakdown[prefix] = DomainBreakdown(
            domain_prefix=prefix, weight=weight
        )
    # Exams bucket by domain (first segment) for MVP; subtopic breakdown comes later.
    for question in session.questions:
        prefix = question.topic_code.split(".")[0] + "."
        domain = breakdown.setdefault(
            prefix, DomainBreakdown(domain_prefix=prefix, weight=domain_weights.get(prefix, 0.0))
        )
        domain.total += 1
        user_ans = session.answers.get(question.id)
        if user_ans is not None and user_ans.is_correct:
            domain.correct += 1

    correct_count = sum(1 for ua in session.answers.values() if ua.is_correct)
    answered = sum(1 for ua in session.answers.values() if ua.answer is not None)
    total = len(session.questions)
    incorrect_count = answered - correct_count
    unanswered_count = total - answered
    # Simple score: correct / total (ignores weights for MVP).
    score = correct_count / total if total > 0 else 0.0
    passed = score >= bank.pass_score

    question_results = {
        q.id: bool(session.answers[q.id].is_correct) if q.id in session.answers else False
        for q in session.questions
    }

    return ExamResult(
        session_id=session.session_id,
        exam_code=bank.code,
        exam_version=bank.version,
        mode=session.mode.value,
        total_questions=total,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        score=score,
        passing_score=bank.pass_score,
        passed=passed,
        domain_breakdown=breakdown,
        question_results=question_results,
    )
