"""Tests for the persistence/stats service (isolated temp SQLite)."""

from pathlib import Path

import pytest

from openboson import stats_service
from openboson.bank_loader import load_exam_bank
from openboson.exsim.scoring import score_exam
from openboson.exsim.session import ExamMode, ExamSession
from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab


@pytest.fixture
def fake_engine(isolated_home):
    """Alias: stats_service is already redirected by ``isolated_home``."""
    return stats_service._engine


@pytest.fixture
def exam_bank():
    bank_path = Path(__file__).resolve().parent / "fixtures" / "sample_bank.yaml"
    return load_exam_bank(bank_path)


@pytest.fixture
def lab():
    lab_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "demo_labs"
        / "ccna_branch_office_access.yaml"
    )
    return load_lab(lab_path)


def test_default_user_created_once(fake_engine):
    u1 = stats_service.get_or_create_default_user()
    u2 = stats_service.get_or_create_default_user()
    assert u1.id == u2.id


def test_save_exam_result(fake_engine, exam_bank):
    sess = ExamSession.create(exam_bank, mode=ExamMode.PRACTICE)
    for q in sess.questions:
        sess.submit_answer(q.id, _correct_answer(q), grade_now=True)
    result = score_exam(sess)
    row_id = stats_service.save_exam_result(sess, result)
    assert row_id > 0
    assert stats_service.exam_summary()["total_exams"] == 1
    assert stats_service.exam_summary()["passed"] >= 1


def test_exam_history(fake_engine, exam_bank):
    sess = ExamSession.create(exam_bank, mode=ExamMode.PRACTICE)
    for q in sess.questions:
        sess.submit_answer(q.id, _correct_answer(q), grade_now=True)
    result = score_exam(sess)
    stats_service.save_exam_result(sess, result)
    history = stats_service.exam_history()
    assert len(history) == 1
    assert history[0].score > 0
    assert history[0].exam_code == exam_bank.code
    assert history[0].exam_code != "exam-None"


def test_practice_attempt_stats(fake_engine):
    stats_service.save_practice_attempt("q1", False)
    stats_service.save_practice_attempt("q1", True)
    stats_service.save_practice_attempt("q2", False)
    m = stats_service.question_stats_map()
    assert m["q1"].seen == 2
    assert m["q1"].misses == 1
    assert m["q1"].last_correct is True
    assert m["q2"].missed
    assert "q3" not in m


def test_save_lab_result(fake_engine, lab):
    sess = LabSession.create(lab)
    for t in lab.tasks:
        sess.submit_task(t.expected_config)
        sess.next_task()
    result = score_lab(sess)
    row_id = stats_service.save_lab_result(sess, result)
    assert row_id > 0
    assert stats_service.lab_summary()["total_labs"] == 1


def test_lab_history(fake_engine, lab):
    sess = LabSession.create(lab)
    for t in lab.tasks:
        sess.submit_task(t.expected_config)
        sess.next_task()
    result = score_lab(sess)
    stats_service.save_lab_result(sess, result)
    history = stats_service.lab_history()
    assert len(history) == 1
    assert history[0].lab_id == lab.lab_id


def _correct_answer(question):
    """Extract the correct answer payload from a Question for submission."""
    from openboson.bank_schema import QuestionType

    ca = question.correct_answer_model
    if question.type == QuestionType.SINGLE_CHOICE:
        return {"answer": ca.answer}
    if question.type == QuestionType.MULTIPLE_CHOICE:
        return {"answers": ca.answers}
    if question.type == QuestionType.DRAG_MATCH:
        return {"pairs": [{"left": p.left, "right": p.right} for p in ca.pairs]}
    if question.type == QuestionType.ORDERED_LIST:
        return {"order": ca.order}
    if question.type == QuestionType.SIM:
        return {"config": "\n".join(ca.expected_commands)}
    return {}
