"""GUI test: Stats page renders with and without data."""

from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.exsim.session import ExamMode
from openboson.gui.main_window import MainWindow


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


@pytest.fixture
def fresh_db(isolated_home):
    """Point stats_service at a temp SQLite so tests are isolated."""
    return isolated_home


def test_stats_page_empty(fresh_db, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Stats")
    page = mw._static_pages["Stats"]
    page.refresh()
    from PySide6.QtWidgets import QLabel

    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any("No exams" in t for t in labels)
    assert any("No labs" in t for t in labels)


def test_stats_page_after_exam(fresh_db, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    bank = load_exam_bank(FIXTURE)
    mw.start_exam_from_list(bank, mode=ExamMode.EXAM)
    sess_page = mw._session_page
    sess = sess_page._session
    from openboson.bank_schema import QuestionType

    for q in sess.questions:
        ca = q.correct_answer_model
        if q.type == QuestionType.SINGLE_CHOICE:
            ans = {"answer": ca.answer}
        elif q.type == QuestionType.MULTIPLE_CHOICE:
            ans = {"answers": ca.answers}
        elif q.type == QuestionType.ORDERED_LIST:
            ans = {"order": ca.order}
        elif q.type == QuestionType.DRAG_MATCH:
            ans = {"pairs": [{"left": p.left, "right": p.right} for p in ca.pairs]}
        elif q.type == QuestionType.SIM:
            ans = {"config": "\n".join(ca.expected_commands or [])}
        else:
            ans = {}
        sess.submit_answer(q.id, ans, grade_now=False)
    sess_page._finish_exam()
    qtbot.wait(100)

    mw.select_page("Stats")
    page = mw._static_pages["Stats"]
    page.refresh()
    from PySide6.QtWidgets import QLabel

    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any("Exams Taken" in t for t in labels)
    assert any("1" == t.strip() for t in labels)
