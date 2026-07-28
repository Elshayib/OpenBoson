"""GUI test: Stats page renders with and without data."""

import pytest

from openboson import stats_service
from openboson.gui.main_window import MainWindow
from openboson.models import Base
from sqlalchemy import create_engine


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Point stats_service at a temp SQLite so tests are isolated."""
    db = tmp_path / "stats_test.db"
    engine = create_engine(f"sqlite:///{db}", future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(stats_service, "_engine", engine)
    yield engine


def test_stats_page_empty(fresh_db, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Stats")
    page = mw._static_pages["Stats"]
    page.refresh()
    # Should show "No exams taken yet" and "No labs completed yet".
    from PySide6.QtWidgets import QLabel
    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any("No exams" in t for t in labels)
    assert any("No labs" in t for t in labels)


def test_stats_page_after_exam(fresh_db, qtbot, monkeypatch):
    # Take an exam through the GUI so it saves to the temp DB.
    mw = MainWindow()
    qtbot.addWidget(mw)
    from openboson.gui.engine import load_available_banks
    from openboson.exsim.session import ExamMode
    bank = load_available_banks()[0]
    mw.start_exam_from_list(bank, mode=ExamMode.STUDY)
    sess_page = mw._session_page
    # Answer all questions correctly via the session.
    sess = sess_page._session
    from openboson.exsim.scoring import grade_answer
    for q in sess.questions:
        from openboson.bank_schema import QuestionType
        ca = q.correct_answer_model
        if q.type == QuestionType.SINGLE_CHOICE:
            ans = {"answer": ca.answer}
        elif q.type == QuestionType.MULTIPLE_CHOICE:
            ans = {"answers": ca.answers}
        else:
            ans = {}
        sess.submit_answer(q.id, ans, study_mode_grade=True)
    sess_page._finish_exam()
    qtbot.wait(100)

    # Now check the Stats page.
    mw.select_page("Stats")
    page = mw._static_pages["Stats"]
    page.refresh()
    from PySide6.QtWidgets import QLabel
    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any("Exams Taken" in t for t in labels)
    assert any("1" == t.strip() for t in labels)
