"""GUI integration test: full exam flow through the main window.

Drives Exams -> ExamSession -> ExamResult -> ExamReview using the in-process
engine facade and pytest-qt. Uses the offscreen platform plugin.
"""

import pytest
from PySide6.QtWidgets import QFrame, QLabel

from openboson.exsim.session import ExamMode
from openboson.gui.engine import load_available_banks
from openboson.gui.main_window import MainWindow


def _correct_answer_for(q):
    correct = q.correct_answer_model
    if q.type.value == "single_choice":
        return {"answer": correct.answer}
    if q.type.value == "multiple_choice":
        return {"answers": list(correct.answers)}
    if q.type.value == "ordered_list":
        return {"order": list(correct.order)}
    if q.type.value == "drag_match":
        return {"pairs": [{"left": p.left, "right": p.right} for p in correct.pairs]}
    if q.type.value == "sim":
        return {"config": "\n".join(correct.expected_commands or [])}
    return None


@pytest.fixture
def window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    return mw


def test_exams_page_lists_demo_bank(window):
    window.select_page("Exams")
    page = window._exams_page
    cards = page.findChildren(QFrame)
    assert len(cards) >= 1


def test_start_exam_shows_session(window, qtbot):
    bank = load_available_banks()[0]
    window.start_exam_from_list(bank, ExamMode.TIMED)
    qtbot.wait(50)
    assert window.visible_page_label() == "Exam"
    qid = window._session_page.current_question_id()
    assert qid is not None


def test_answer_and_finish_flow(window, qtbot):
    bank = load_available_banks()[0]
    window.start_exam_from_list(bank, ExamMode.TIMED)
    qtbot.wait(50)

    sess = window._session_page._session
    for q in list(sess.questions):
        window._session_page._store_answer(q.id, _correct_answer_for(q))
    window._session_page._finish_exam()
    qtbot.wait(50)

    assert window.visible_page_label() == "Result"
    labels = window._result_page.findChildren(QLabel)
    assert any("PASSED" in (l.text() or "") for l in labels)


def test_result_to_review(window, qtbot):
    bank = load_available_banks()[0]
    window.start_exam_from_list(bank, ExamMode.TIMED)
    qtbot.wait(50)
    sess = window._session_page._session
    for q in list(sess.questions):
        window._session_page._store_answer(q.id, _correct_answer_for(q))
    window._session_page._finish_exam()
    qtbot.wait(50)
    window._on_review(sess)
    qtbot.wait(50)
    assert window.visible_page_label() == "Review"
    cards = window._review_page.findChildren(QFrame)
    assert len(cards) >= 1


def test_question_card_emits_answer_on_radio(qtbot):
    from pathlib import Path

    from openboson.bank_loader import load_exam_bank
    from openboson.gui.widgets.question_card import QuestionCard

    path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "demo_banks"
        / "ccna_200_301_v1.1_demo.yaml"
    )
    bank = load_exam_bank(path)
    q = next(qq for qq in bank.questions if qq.type.value == "single_choice")
    card = QuestionCard(q)
    qtbot.addWidget(card)
    with qtbot.waitSignal(card.answerChanged, timeout=1000) as sig:
        card._radio_group.buttons()[0].setChecked(True)
    emitted = sig.args[0]
    assert emitted["answer"] == q.correct_answer_model.answer
