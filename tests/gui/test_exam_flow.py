"""GUI integration test: practice library + exam flow through the main window."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from openboson.bank_loader import load_exam_bank
from openboson.exsim.session import ExamMode
from openboson.gui.main_window import MainWindow


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


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


def test_practice_page_lists_questions(window):
    window.select_page("Practice")
    page = window._practice_page
    page.refresh()
    assert "question" in page._count_lbl.text().lower()
    cards = page.findChildren(QFrame)
    assert len(cards) >= 1
    # Exam CTAs present
    buttons = [b.text() for b in page.findChildren(QPushButton)]
    assert any("200-301" in t for t in buttons)
    assert any("350-401" in t for t in buttons)


def test_start_exam_shows_session(window, qtbot):
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
    qtbot.wait(50)
    assert window.visible_page_label() == "Exam"
    qid = window._session_page.current_question_id()
    assert qid is not None


def test_answer_and_finish_flow(window, qtbot):
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
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
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
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


def test_practice_question_check_shows_feedback(window, qtbot):
    bank = load_exam_bank(FIXTURE)
    q = next(qq for qq in bank.questions if qq.type.value == "single_choice")
    window._on_practice_question(q)
    qtbot.wait(50)
    assert window.visible_page_label() == "Practice Question"
    page = window._practice_q_page
    page._card.set_answer({"answer": q.correct_answer_model.answer})
    page._check_answer()
    qtbot.wait(50)
    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any(t == "Correct" for t in labels)


def test_question_card_emits_answer_on_radio(qtbot):
    from openboson.gui.widgets.question_card import QuestionCard

    bank = load_exam_bank(FIXTURE)
    q = next(qq for qq in bank.questions if qq.type.value == "single_choice")
    card = QuestionCard(q)
    qtbot.addWidget(card)
    with qtbot.waitSignal(card.answerChanged, timeout=1000) as sig:
        card._radio_group.buttons()[0].setChecked(True)
    emitted = sig.args[0]
    assert emitted["answer"] == q.correct_answer_model.answer
