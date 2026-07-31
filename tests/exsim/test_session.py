"""Tests for ExamSession state machine."""

from __future__ import annotations

import random
from collections import Counter

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.bank_schema import ExamBank, QuestionType
from openboson.exsim.blueprint import InsufficientPoolError
from openboson.exsim.scoring import grade_answer
from openboson.exsim.session import ExamMode, ExamSession, build_question_presentation


@pytest.fixture
def bank() -> ExamBank:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"
    return load_exam_bank(path)


def test_create_session_shuffles_questions(bank):
    s = ExamSession.create(bank)
    assert s.exam is bank
    assert len(s.questions) == len(bank.questions)
    assert {q.id for q in s.questions} == {q.id for q in bank.questions}


def test_create_session_has_unique_ids(bank):
    s1 = ExamSession.create(bank)
    s2 = ExamSession.create(bank)
    assert s1.session_id != s2.session_id


def test_current_question_returns_first(bank):
    s = ExamSession.create(bank)
    assert s.current_question is s.questions[0]


def test_next_previous_navigation(bank):
    s = ExamSession.create(bank)
    q1 = s.current_question
    q2 = s.next()
    assert q2 is not None
    assert q2 is s.current_question
    assert q2 is not q1
    q_back = s.previous()
    assert q_back is q1


def test_next_at_end_returns_none(bank):
    s = ExamSession.create(bank)
    s.goto(len(s.questions) - 1)
    assert s.next() is None


def test_goto_invalid_raises(bank):
    s = ExamSession.create(bank)
    with pytest.raises(IndexError):
        s.goto(999)
    with pytest.raises(IndexError):
        s.goto(-1)


def test_submit_answer_exam_mode_not_graded(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM)
    q = s.current_question
    s.submit_answer(q.id, {"answer": "a"} if q.type.value == "single_choice" else {"answers": []})
    assert s.answers[q.id].is_correct is None
    assert s.answered_count() == 1


def test_submit_answer_practice_mode_graded_immediately(bank):
    s = ExamSession.create(bank, mode=ExamMode.PRACTICE)
    q = next(qq for qq in s.questions if qq.type.value == "single_choice")
    s.submit_answer(q.id, {"answer": q.correct_answer_model.answer})
    assert s.answers[q.id].is_correct is True


def test_toggle_bookmark(bank):
    s = ExamSession.create(bank)
    q = s.current_question
    assert s.toggle_bookmark(q.id) is True
    assert q.id in s.bookmarked
    assert s.toggle_bookmark(q.id) is False
    assert q.id not in s.bookmarked


def test_toggle_mark_for_review(bank):
    s = ExamSession.create(bank)
    q = s.current_question
    assert s.toggle_mark_for_review(q.id) is True
    assert q.id in s.marked_for_review


def test_finish_marks_session(bank):
    s = ExamSession.create(bank)
    assert not s.is_finished()
    s.finish()
    assert s.is_finished()
    assert s.finished_at is not None


def test_explicit_empty_questions_raises(bank):
    with pytest.raises(InsufficientPoolError, match="empty question set"):
        ExamSession.create(bank, questions=[])


def test_presentation_stable_within_session(bank):
    s = ExamSession.create(bank, seed=42, shuffle=False)
    q = next(qq for qq in s.questions if qq.type == QuestionType.SINGLE_CHOICE)
    p1 = s.presentation_for(q.id)
    p2 = s.presentation_for(q.id)
    assert p1 is not None and p2 is not None
    assert p1.choice_ids == p2.choice_ids
    assert set(p1.choice_ids or []) == {c.id for c in (q.choices or [])}


def test_presentation_varies_across_sessions(bank):
    q = next(qq for qq in bank.questions if qq.type == QuestionType.SINGLE_CHOICE)
    orders = set()
    for seed in range(20):
        s = ExamSession.create(bank, seed=seed, shuffle=False, questions=[q])
        orders.add(tuple(s.presentation_for(q.id).choice_ids or []))  # type: ignore[union-attr]
    assert len(orders) > 1


def test_presentation_does_not_change_grading(bank):
    q = next(qq for qq in bank.questions if qq.type == QuestionType.SINGLE_CHOICE)
    correct = {"answer": q.correct_answer_model.answer}
    wrong = {"answer": next(c.id for c in q.choices if c.id != q.correct_answer_model.answer)}
    for seed in (0, 1, 7, 99):
        s = ExamSession.create(bank, seed=seed, shuffle=False, questions=[q])
        assert grade_answer(q, correct) is True
        assert grade_answer(q, wrong) is False
        assert s.submit_answer(q.id, correct, grade_now=True) is True


def test_drag_presentation_independent_sides(bank):
    q = next(qq for qq in bank.questions if qq.type == QuestionType.DRAG_MATCH)
    s = ExamSession.create(bank, seed=3, shuffle=False, questions=[q])
    pres = s.presentation_for(q.id)
    assert pres is not None
    assert pres.drag_left is not None and pres.drag_right is not None
    left_ids = {d.id for d in pres.drag_left}
    right_ids = {d.id for d in pres.drag_right}
    assert left_ids.isdisjoint(right_ids)
    dumped = pres.to_dict()
    assert "drag_pairs" not in dumped
    assert len(dumped["left_items"]) == len(dumped["right_items"])


def test_ordered_presentation_stable(bank):
    q = next(qq for qq in bank.questions if qq.type == QuestionType.ORDERED_LIST)
    s = ExamSession.create(bank, seed=5, shuffle=False, questions=[q])
    a = s.presentation_for(q.id).ordered_items  # type: ignore[union-attr]
    b = s.presentation_for(q.id).ordered_items  # type: ignore[union-attr]
    assert a == b
    assert set(a or []) == set(q.ordered_items or [])


def test_choice_position_distribution_guard(bank):
    """Correct answers should not always sit in one authored display slot."""
    q = next(qq for qq in bank.questions if qq.type == QuestionType.SINGLE_CHOICE)
    correct_id = q.correct_answer_model.answer
    positions: Counter[int] = Counter()
    for seed in range(40):
        pres = build_question_presentation(q, rng=random.Random(seed))
        pos = (pres.choice_ids or []).index(correct_id)
        positions[pos] += 1
    assert len(positions) >= 2
