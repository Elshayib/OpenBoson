"""Tests for ExamSession state machine."""

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.bank_schema import ExamBank
from openboson.exsim.session import ExamMode, ExamSession


@pytest.fixture
def bank() -> ExamBank:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "demo_banks" / "ccna_200_301_v1.1_demo.yaml"
    return load_exam_bank(path)


def test_create_session_shuffles_questions(bank):
    s = ExamSession.create(bank)
    assert s.exam is bank
    assert len(s.questions) == len(bank.questions)
    # IDs present (sets equal) but order likely shuffled.
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
    # Jump to last
    s.goto(len(s.questions) - 1)
    assert s.next() is None


def test_goto_invalid_raises(bank):
    s = ExamSession.create(bank)
    with pytest.raises(IndexError):
        s.goto(999)
    with pytest.raises(IndexError):
        s.goto(-1)


def test_submit_answer_timed_mode_not_graded(bank):
    s = ExamSession.create(bank, mode=ExamMode.TIMED)
    q = s.current_question
    s.submit_answer(q.id, {"answer": "a"} if q.type.value == "single_choice" else {"answers": []})
    # In timed mode, grading is deferred.
    assert s.answers[q.id].is_correct is None
    assert s.answered_count() == 1


def test_submit_answer_study_mode_graded_immediately(bank):
    s = ExamSession.create(bank, mode=ExamMode.STUDY)
    # Find a single_choice question so we know the right answer shape.
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
