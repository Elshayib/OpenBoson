"""Tests for the persistence/stats service (in-memory SQLite)."""

import pytest

from openboson import stats_service
from openboson.bank_loader import load_exam_bank
from openboson.db import init_db
from openboson.exsim.scoring import score_exam
from openboson.exsim.session import ExamMode, ExamSession
from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab
from openboson.models import Base
from sqlalchemy import create_engine


@pytest.fixture
def fake_engine(tmp_path):
    """Use a temp-file SQLite so multiple sessions share the same DB."""
    db = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db}", future=True)
    Base.metadata.create_all(engine)
    # Monkeypatch the module-level engine so all helpers use it.
    stats_service._engine = engine
    yield engine
    stats_service._engine = None


@pytest.fixture
def exam_bank():
    from pathlib import Path
    bank_path = Path(__file__).resolve().parents[1] / "data" / "demo_banks" / "ccna_200_301_v1.1_demo.yaml"
    return load_exam_bank(bank_path)


@pytest.fixture
def lab():
    from pathlib import Path
    lab_path = Path(__file__).resolve().parents[1] / "data" / "demo_labs" / "ccna_basic_rtr_sw.yaml"
    return load_lab(lab_path)


def test_default_user_created_once(fake_engine):
    u1 = stats_service.get_or_create_default_user()
    u2 = stats_service.get_or_create_default_user()
    assert u1.id == u2.id


def test_save_exam_result(fake_engine, exam_bank):
    sess = ExamSession.create(exam_bank, mode=ExamMode.STUDY)
    # Answer all questions correctly.
    for q in sess.questions:
        sess.submit_answer(q.id, _correct_answer(q), study_mode_grade=True)
    result = score_exam(sess)
    row_id = stats_service.save_exam_result(sess, result)
    assert row_id > 0
    assert stats_service.exam_summary()["total_exams"] == 1
    assert stats_service.exam_summary()["passed"] >= 1


def test_exam_history(fake_engine, exam_bank):
    sess = ExamSession.create(exam_bank, mode=ExamMode.STUDY)
    for q in sess.questions:
        sess.submit_answer(q.id, _correct_answer(q), study_mode_grade=True)
    result = score_exam(sess)
    stats_service.save_exam_result(sess, result)
    history = stats_service.exam_history()
    assert len(history) == 1
    assert history[0].score > 0


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
