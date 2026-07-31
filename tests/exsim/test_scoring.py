"""Tests for exam scoring."""

from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.bank_schema import ExamBank, Question
from openboson.exsim.scoring import (
    ExamResult,
    grade_answer,
    score_exam,
)
from openboson.exsim.session import ExamMode, ExamSession

BANK_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


@pytest.fixture
def bank() -> ExamBank:
    return load_exam_bank(BANK_PATH)


def _q(bank: ExamBank, qid: str) -> Question:
    return next(q for q in bank.questions if q.id == qid)


def test_grade_single_choice_correct(bank):
    q = _q(bank, "q1")
    assert grade_answer(q, {"answer": "a"}) is True


def test_grade_single_choice_incorrect(bank):
    q = _q(bank, "q1")
    assert grade_answer(q, {"answer": "b"}) is False


def test_grade_single_choice_with_plain_string(bank):
    q = _q(bank, "q1")
    assert grade_answer(q, "a") is True
    assert grade_answer(q, "c") is False


def test_grade_single_choice_none_answer_is_false(bank):
    q = _q(bank, "q1")
    assert grade_answer(q, None) is False


def test_grade_multiple_choice_exact_match(bank):
    q = _q(bank, "q2")
    assert grade_answer(q, {"answers": ["a", "c"]}) is True


def test_grade_multiple_choice_partial_wrong(bank):
    q = _q(bank, "q2")
    assert grade_answer(q, {"answers": ["a"]}) is False  # missing c
    assert grade_answer(q, {"answers": ["a", "c", "b"]}) is False  # extra b


def test_grade_multiple_choice_list_form(bank):
    q = _q(bank, "q2")
    assert grade_answer(q, ["a", "c"]) is True


def test_grade_ordered_list_correct(bank):
    q = _q(bank, "q3")
    correct_order = q.correct_answer_model.order
    assert grade_answer(q, {"order": list(correct_order)}) is True


def test_grade_ordered_list_wrong(bank):
    q = _q(bank, "q3")
    correct_order = list(q.correct_answer_model.order)
    wrong = list(reversed(correct_order))
    assert grade_answer(q, {"order": wrong}) is False


def test_grade_drag_match_all_correct(bank):
    q = _q(bank, "q4")
    pairs = q.correct_answer_model.pairs
    payload = [{"left": p.left, "right": p.right} for p in pairs]
    # Shuffle to confirm order-independent.
    shuffled = payload[::-1]
    assert grade_answer(q, {"pairs": shuffled}) is True


def test_grade_drag_match_one_wrong(bank):
    q = _q(bank, "q4")
    pairs = q.correct_answer_model.pairs
    payload = [{"left": p.left, "right": p.right} for p in pairs]
    payload[0]["right"] = "WRONG"
    assert grade_answer(q, {"pairs": payload}) is False


def test_grade_sim_correct(bank):
    q = _q(bank, "q5")
    expected = q.correct_answer_model
    text = "\n".join(expected.expected_commands)
    assert grade_answer(q, {"config": text}) is True


def test_grade_sim_missing_command(bank):
    q = _q(bank, "q5")
    expected = q.correct_answer_model
    # Remove one command.
    cmds = list(expected.expected_commands)
    cmds = cmds[:-1]
    text = "\n".join(cmds)
    assert grade_answer(q, {"config": text}) is False


def test_score_exam_all_correct_passes(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM)
    # Replace shuffled order with exam order to grade deterministically.
    s.questions = list(bank.questions)
    for q in s.questions:
        correct = q.correct_answer_model
        if q.type.value == "single_choice":
            ans = {"answer": correct.answer}
        elif q.type.value == "multiple_choice":
            ans = {"answers": list(correct.answers)}
        elif q.type.value == "ordered_list":
            ans = {"order": list(correct.order)}
        elif q.type.value == "drag_match":
            ans = {"pairs": [{"left": p.left, "right": p.right} for p in correct.pairs]}
        else:  # sim
            ans = {"config": "\n".join(correct.expected_commands)}
        s.submit_answer(q.id, ans)
    s.finish()
    result = score_exam(s)
    assert isinstance(result, ExamResult)
    assert result.total_questions == 6
    assert result.correct_count == 6
    assert result.incorrect_count == 0
    assert result.unanswered_count == 0
    assert result.score == pytest.approx(1.0)
    assert result.passed is True


def test_score_exam_all_wrong_fails(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM)
    s.questions = list(bank.questions)
    for q in s.questions:
        s.submit_answer(
            q.id,
            {"answer": "__definitely_wrong__"}
            if q.type.value == "single_choice"
            else {"answers": ["__bad__"]},
        )
    s.finish()
    result = score_exam(s)
    assert result.score == pytest.approx(0.0)
    assert result.passed is False
    assert result.incorrect_count == result.total_questions


def test_score_exam_unanswered_does_not_score(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM)
    s.questions = list(bank.questions)
    # Answer only first two questions.
    q1 = s.questions[0]
    s.submit_answer(q1.id, {"answer": "__bad__"})
    s.finish()
    result = score_exam(s)
    assert result.total_questions == 6
    assert result.unanswered_count == 5


def test_score_exam_domain_breakdown_populated(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM)
    s.questions = list(bank.questions)
    # Answer all correctly.
    for q in s.questions:
        correct = q.correct_answer_model
        if q.type.value == "single_choice":
            ans = {"answer": correct.answer}
        elif q.type.value == "multiple_choice":
            ans = {"answers": list(correct.answers)}
        elif q.type.value == "ordered_list":
            ans = {"order": list(correct.order)}
        elif q.type.value == "drag_match":
            ans = {"pairs": [{"left": p.left, "right": p.right} for p in correct.pairs]}
        else:
            ans = {"config": "\n".join(correct.expected_commands)}
        s.submit_answer(q.id, ans)
    s.finish()
    result = score_exam(s)
    # Six domains present.
    assert len(result.domain_breakdown) == 6
    assert all(d.total >= 1 for d in result.domain_breakdown.values())
    # Domain weights sum to 1.0 (CCNA blueprint).
    total_weight = sum(d.weight for d in result.domain_breakdown.values())
    assert total_weight == pytest.approx(1.0)


def test_exam_result_score_percent_is_score_times_100(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM)
    s.questions = list(bank.questions)
    s.submit_answer(s.questions[0].id, {"answer": "__bad__"})
    s.finish()
    result = score_exam(s)
    assert result.score_percent == result.score * 100.0


def test_grade_sim_no_expected_commands_returns_false(bank):
    """Sims without expected_commands cannot be auto-graded; return False."""
    from openboson.bank_schema import Question, QuestionType

    # Build a minimal sim question without expected_commands.
    q = Question(
        id="x",
        type=QuestionType.SIM,
        topic_code="5.0",
        cert_tags=["ccna"],
        stem="placeholder",
        sim=None,
        correct={"instructions": "do something"},
    )
    assert grade_answer(q, {"config": "anything"}) is False
