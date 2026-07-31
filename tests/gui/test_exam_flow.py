"""GUI integration test: practice library + exam flow through the main window."""

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QScrollArea

from openboson.bank_loader import load_exam_bank
from openboson.bank_schema import ExamBank, QuestionType
from openboson.exsim.session import ExamMode, ExamSession
from openboson.gui.main_window import MainWindow
from openboson.gui.widgets.question_card import QuestionCard

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


pytestmark = pytest.mark.usefixtures("isolated_home")


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
    # Pagination controls exist for large pools
    assert page._page_size == 50
    assert "Page" in page._page_lbl.text()
    if len(page._filtered) > page._page_size:
        assert page._next_page.isEnabled()


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
    assert any("PASSED" in (lbl.text() or "") for lbl in labels)


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
    cards = window._review_page.review_cards()
    assert len(cards) >= 1
    assert window._review_page.scroll_area() is not None


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
    labels = [lbl.text() for lbl in page.findChildren(QLabel)]
    assert any(t == "Correct" for t in labels)


def test_question_card_emits_answer_on_radio(qtbot):
    bank = load_exam_bank(FIXTURE)
    q = next(qq for qq in bank.questions if qq.type.value == "single_choice")
    card = QuestionCard(q)
    qtbot.addWidget(card)
    btn = card._radio_group.buttons()[0]
    expected_id = btn.property("choice_id")
    with qtbot.waitSignal(card.answerChanged, timeout=1000) as sig:
        btn.setChecked(True)
    emitted = sig.args[0]
    assert emitted["answer"] == expected_id


def test_drag_match_duplicate_rights_restore(qtbot):
    """Both Server → Client slots must restore (ccna-4-001 style duplicates)."""
    bank = load_exam_bank(FIXTURE)
    q = next(qq for qq in bank.questions if qq.id == "q4")
    rights = [p.right for p in q.drag_pairs]
    assert rights.count("Server → Client") == 2

    card = QuestionCard(q)
    qtbot.addWidget(card)
    answer = {
        "pairs": [
            {"left": "DISCOVER", "right": "Client → Server (broadcast)"},
            {"left": "OFFER", "right": "Server → Client"},
            {"left": "REQUEST", "right": "Client → Server"},
            {"left": "ACK", "right": "Server → Client"},
        ]
    }
    card.set_answer(answer)
    qtbot.wait(50)

    slots = card._match_widget._slots
    filled = [s.right_value() for s in slots]
    assert filled.count("Server → Client") == 2
    assert all(v is not None for v in filled)
    assert card._match_widget._pool.count() == 0

    # Clearing one duplicate returns exactly one token to the pool.
    offer_slot = next(s for s in slots if s.left_label == "OFFER")
    offer_slot.clear()
    assert offer_slot.right_value() is None
    assert card._match_widget._pool.count() == 1
    ack_slot = next(s for s in slots if s.left_label == "ACK")
    assert ack_slot.right_value() == "Server → Client"


def test_ordered_list_next_back_preserves_order(window, qtbot):
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
    qtbot.wait(50)
    sess = window._session_page._session
    idx = next(i for i, q in enumerate(sess.questions) if q.type == QuestionType.ORDERED_LIST)
    window._session_page._jump(idx)
    qtbot.wait(50)

    stored = sess.answers[sess.questions[idx].id].answer
    assert stored is not None and "order" in stored
    first_order = list(stored["order"])

    # Navigate away and back — order must not reshuffle or clear.
    if idx + 1 < len(sess.questions):
        window._session_page._go_next()
    else:
        window._session_page._go_prev()
    qtbot.wait(50)
    window._session_page._jump(idx)
    qtbot.wait(50)

    restored = sess.answers[sess.questions[idx].id].answer["order"]
    assert restored == first_order
    card = window._session_page._current_card
    assert card.current_answer()["order"] == first_order


def test_review_scroll_reaches_final_card(window, qtbot):
    """100-question review content lives in a QScrollArea and can reach the last card."""
    bank = load_exam_bank(FIXTURE)
    template = bank.questions[0]
    many = []
    for i in range(100):
        q = template.model_copy(deep=True)
        q.id = f"scroll-q-{i}"
        q.stem = f"Review stem number {i + 1}"
        many.append(q)
    big = ExamBank(
        title=bank.title,
        code=bank.code,
        version=bank.version,
        provider=bank.provider,
        description=bank.description,
        pass_score=bank.pass_score,
        time_limit_minutes=bank.time_limit_minutes,
        topics=bank.topics,
        questions=many,
    )
    session = ExamSession.create(big, mode=ExamMode.EXAM, shuffle=False, questions=many)
    for q in many:
        session.submit_answer(q.id, _correct_answer_for(q), grade_now=True)
    session.finish()

    window._on_review(session)
    qtbot.wait(100)
    assert window.visible_page_label() == "Review"

    scroll = window._review_page.scroll_area()
    assert isinstance(scroll, QScrollArea)
    cards = window._review_page.review_cards()
    assert len(cards) == 100

    last = cards[-1]
    scroll.ensureWidgetVisible(last)
    qtbot.wait(50)
    QApplication.processEvents()

    # Viewport should include the bottom of the final card.
    vp = scroll.viewport()
    top_left = last.mapTo(vp, QPoint(0, 0))
    bottom_y = top_left.y() + last.height()
    assert top_left.y() < vp.height()
    assert bottom_y > 0


def test_active_exam_blocks_sidebar_nav(window, qtbot):
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
    qtbot.wait(50)
    assert window._exam_active
    assert window.visible_page_label() == "Exam"

    window.select_page("Dashboard")
    qtbot.wait(50)
    assert window.visible_page_label() == "Exam"
    assert window._exam_active


def test_hidden_timeout_does_not_switch_pages(window, qtbot):
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
    qtbot.wait(50)
    finished = []
    window._session_page.set_on_result(lambda s, r: finished.append((s, r)))

    # Leaving the exam stops the timer and clears the timeout callback.
    window._leave_exam()
    window._stack.setCurrentWidget(window._static_pages["Dashboard"])
    qtbot.wait(50)

    window._session_page._on_timeout()
    qtbot.wait(50)
    assert finished == []
    assert window.visible_page_label() == "Dashboard"


def test_retake_fallback_starts_exam_once(window, qtbot, monkeypatch):
    bank = load_exam_bank(FIXTURE)
    window.start_exam_from_list(bank, ExamMode.EXAM)
    qtbot.wait(50)
    sess = window._session_page._session
    for q in list(sess.questions):
        window._session_page._store_answer(q.id, _correct_answer_for(q))
    window._session_page._finish_exam()
    qtbot.wait(50)
    assert window.visible_page_label() == "Result"

    sess.blueprint_id = "ccna"
    starts: list[int] = []
    real_start = window._session_page.start_exam

    def counting_start(*args, **kwargs):
        starts.append(1)
        return real_start(*args, **kwargs)

    monkeypatch.setattr(window._session_page, "start_exam", counting_start)

    def boom(_blueprint_id: str):
        raise RuntimeError("blueprint unavailable")

    monkeypatch.setattr("openboson.gui.engine.start_blueprint_exam", boom)

    window._on_retake(sess)
    qtbot.wait(50)
    assert len(starts) == 1
    assert window.visible_page_label() == "Exam"
    assert window._exam_active
