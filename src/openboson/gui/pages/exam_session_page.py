"""Exam session page — interactive question-by-question exam taking UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import Question
from openboson.exsim.scoring import ExamResult
from openboson.exsim.session import ExamMode, ExamSession
from openboson.gui.engine import finish_and_score, start_session
from openboson.gui.widgets.question_card import QuestionCard
from openboson.gui.widgets.timer_bar import TimerBar


class ExamSessionPage(QWidget):
    """Drives an in-progress exam: question nav, bookmark, submit, finish."""

    title = "Exam"

    def __init__(self) -> None:
        super().__init__()
        self._session: ExamSession | None = None
        self._on_result: callable | None = None
        self._on_exit: callable | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar: timer + question number + bookmark
        self._top = QHBoxLayout()
        self._top.setContentsMargins(24, 16, 24, 16)
        self._qnum = QLabel("")
        self._qnum.setProperty("role", "h2")
        self._top.addWidget(self._qnum)
        self._top.addStretch()
        self._timer = TimerBar(1)
        self._timer.set_on_timeout(self._on_timeout)
        self._top.addWidget(self._timer, 1)
        self._bookmark_btn = QPushButton("☆ Bookmark")
        self._bookmark_btn.setObjectName("Secondary")
        self._bookmark_btn.clicked.connect(self._toggle_bookmark)
        self._top.addWidget(self._bookmark_btn)
        root.addLayout(self._top)

        # Question area (scrollable)
        self._card_holder = QFrame()
        self._card_holder.setObjectName("CardHolder")
        card_layout = QVBoxLayout(self._card_holder)
        card_layout.setContentsMargins(24, 16, 24, 16)
        self._card_layout = card_layout
        root.addWidget(self._card_holder, 1)

        # Bottom nav
        self._bottom = QHBoxLayout()
        self._bottom.setContentsMargins(24, 16, 24, 16)
        self._prev = QPushButton("‹ Previous")
        self._prev.setObjectName("Secondary")
        self._prev.clicked.connect(self._go_prev)
        self._next = QPushButton("Next ›")
        self._next.setObjectName("Secondary")
        self._next.clicked.connect(self._go_next)
        self._finish = QPushButton("Finish Exam")
        self._finish.setObjectName("Primary")
        self._finish.clicked.connect(self._finish_exam)
        self._bottom.addWidget(self._prev)
        self._bottom.addWidget(self._next)
        self._bottom.addStretch()
        self._bottom.addWidget(self._finish)
        root.addLayout(self._bottom)

    # -----/ Lifecycle /-----
    def start_exam(self, bank, mode: ExamMode = ExamMode.TIMED) -> None:
        self._session = start_session(bank, mode=mode)
        self._timer = TimerBar(len(self._session.questions), limit_minutes=bank.time_limit_minutes)
        self._timer.set_on_timeout(self._on_timeout)
        self._render_current()
        self._timer.start()

    def set_on_result(self, callback) -> None:
        self._on_result = callback

    def set_on_exit(self, callback) -> None:
        self._on_exit = callback

    def cleanup(self) -> None:
        self._timer.stop()

    # -----/ Rendering /-----
    def _render_current(self) -> None:
        if self._session is None:
            return
        sess = self._session
        q = sess.current_question
        # Clear old card.
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        card = QuestionCard(q)
        # Restore a previously stored answer for this question.
        existing = sess.answers.get(q.id)
        if existing is not None:
            card.set_answer(existing.answer)
        card.answerChanged.connect(lambda ans, qid=q.id: self._store_answer(qid, ans))
        self._card_layout.addWidget(card)
        self._current_card = card

        self._qnum.setText(f"Question {sess.current_index + 1} / {len(sess.questions)}")
        self._timer.set_progress(sess.answered_count())
        self._update_bookmark_button()
        self._prev.setEnabled(sess.current_index > 0)
        self._next.setEnabled(sess.current_index < len(sess.questions) - 1)

    def _store_answer(self, qid: str, answer) -> None:
        if self._session is None:
            return
        # In timed mode we don't grade yet; in study mode grade immediately.
        self._session.submit_answer(
            qid, answer, study_mode_grade=(self._session.mode == ExamMode.STUDY)
        )
        self._timer.set_progress(self._session.answered_count())

    def _toggle_bookmark(self) -> None:
        if self._session is None:
            return
        q = self._session.current_question
        self._session.toggle_bookmark(q.id)
        self._update_bookmark_button()

    def _update_bookmark_button(self) -> None:
        if self._session is None:
            return
        q = self._session.current_question
        if q.id in self._session.bookmarked:
            self._bookmark_btn.setText("★ Bookmarked")
        else:
            self._bookmark_btn.setText("☆ Bookmark")

    def _go_prev(self) -> None:
        if self._session is None:
            return
        if self._session.previous() is not None:
            self._render_current()

    def _go_next(self) -> None:
        if self._session is None:
            return
        if self._session.next() is not None:
            self._render_current()

    def _on_timeout(self) -> None:
        # Time is up — auto-finish.
        self._finish_exam()

    def _finish_exam(self) -> None:
        if self._session is None:
            return
        self._timer.stop()
        result = finish_and_score(self._session)
        if self._on_result:
            self._on_result(self._session, result)

    # -----/ Test hooks /-----
    def current_question_id(self) -> str | None:
        if self._session is None:
            return None
        return self._session.current_question.id

    def answer_current(self, answer) -> None:
        """Test helper: submit an answer for the current question."""
        if self._session is None:
            return
        qid = self._session.current_question.id
        self._store_answer(qid, answer)
