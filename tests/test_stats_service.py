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


def test_save_exam_persists_objective_identity(fake_engine, exam_bank):
    from openboson.db import get_sessionmaker
    from openboson.models import UserAnswer

    sess = ExamSession.create(exam_bank, mode=ExamMode.PRACTICE)
    for q in sess.questions:
        sess.submit_answer(q.id, _correct_answer(q), grade_now=True)
    result = score_exam(sess)
    row_id = stats_service.save_exam_result(sess, result)

    Session = get_sessionmaker(stats_service._engine)
    with Session() as s:
        answers = s.query(UserAnswer).filter(UserAnswer.session_id == row_id).all()
    by_id = {a.bank_question_id: a for a in answers}
    for q in sess.questions:
        saved = by_id[q.id]
        assert saved.topic_code == q.topic_code
        assert saved.cert_tag == q.cert_tags[0]
        assert saved.exam_version == exam_bank.version


def test_weak_domains_after_failed_exam(fake_engine, exam_bank):
    """Fail every question → each domain is weak with 0% accuracy."""
    sess = ExamSession.create(exam_bank, mode=ExamMode.EXAM)
    for q in sess.questions:
        sess.submit_answer(q.id, _wrong_answer(q), grade_now=True)
    result = score_exam(sess)
    assert result.score < 1.0
    stats_service.save_exam_result(sess, result)

    domains = stats_service.domain_totals()
    assert domains
    assert all(d.percent == 0.0 for d in domains)
    assert all(d.total_questions > 0 for d in domains)

    weak = stats_service.weak_domains(limit=5)
    assert weak
    assert weak[0].percent == 0.0

    ccna_weak = stats_service.weak_domains(cert="ccna", limit=5)
    assert ccna_weak
    assert all(d.cert_tag == "ccna" for d in ccna_weak)

    missed = stats_service.recent_missed_question_ids(limit=50)
    assert set(missed) == {q.id for q in sess.questions}

    trend = stats_service.score_trend(limit=5)
    assert len(trend) == 1
    assert trend[0].score == result.score


def test_weak_domains_empty_without_history(fake_engine):
    assert stats_service.weak_domains() == []
    assert stats_service.recent_missed_question_ids() == []
    assert stats_service.score_trend() == []
    assert stats_service.latest_activity() is None


def _wrong_answer(question):
    """Return an incorrect payload so grading marks the question wrong."""
    from openboson.bank_schema import QuestionType

    ca = question.correct_answer_model
    if question.type == QuestionType.SINGLE_CHOICE:
        wrong = next(
            (c.id for c in (question.choices or []) if c.id != ca.answer),
            "__wrong__",
        )
        return {"answer": wrong}
    if question.type == QuestionType.MULTIPLE_CHOICE:
        return {"answers": []}
    if question.type == QuestionType.DRAG_MATCH:
        return {"pairs": []}
    if question.type == QuestionType.ORDERED_LIST:
        return {"order": list(reversed(ca.order))}
    if question.type == QuestionType.SIM:
        return {"config": "hostname WRONG"}
    return {}


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
