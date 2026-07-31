"""Exam session page — silent blueprint exam taking UI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import QuestionType
from openboson.exsim.session import ExamMode, ExamSession
from openboson.gui.engine import finish_and_score, pause_session, save_active_session
from openboson.gui.widgets.question_card import QuestionCard
from openboson.gui.widgets.timer_bar import TimerBar


def _presentation_for(session: ExamSession, question_id: str) -> dict[str, Any] | None:
    """Resolve engine presentation as a dict (``presentation_for().to_dict()``)."""
    data = session.presentation_for(question_id)
    if data is None:
        return None
    return data.to_dict()


class ExamSessionPage(QWidget):
    """Drives an in-progress exam: question nav, grid, bookmark, finish."""

    title = "Exam"

    def __init__(self) -> None:
        super().__init__()
        self._session: ExamSession | None = None
        self._on_result: Callable[..., Any] | None = None
        self._on_exit: Callable[..., Any] | None = None
        self._current_card: QuestionCard | None = None
        self._active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar — question number + timer only (actions live in bottom bar)
        self._top = QHBoxLayout()
        self._top.setContentsMargins(24, 16, 24, 16)
        self._qnum = QLabel("")
        self._qnum.setProperty("role", "h2")
        self._top.addWidget(self._qnum)
        self._top.addStretch()
        self._timer_host = QHBoxLayout()
        self._timer = TimerBar(1)
        self._timer.set_on_timeout(self._on_timeout)
        self._timer_host.addWidget(self._timer, 1)
        self._top.addLayout(self._timer_host, 1)
        root.addLayout(self._top)

        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)

        # Question grid sidebar
        grid_wrap = QFrame()
        grid_wrap.setObjectName("Sidebar")
        grid_wrap.setMinimumWidth(160)
        grid_wrap.setMaximumWidth(220)
        gw = QVBoxLayout(grid_wrap)
        gw.setContentsMargins(8, 8, 8, 8)
        gw.addWidget(QLabel("Questions"))
        self._grid_host = QWidget()
        self._grid_layout = QGridLayout(self._grid_host)
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._grid_host)
        gw.addWidget(scroll, 1)
        mid.addWidget(grid_wrap)

        # Question area — scroll so tall cards (drag-match / sim) never clip
        self._card_holder = QFrame()
        self._card_holder.setObjectName("CardHolder")
        card_outer = QVBoxLayout(self._card_holder)
        card_outer.setContentsMargins(0, 0, 0, 0)
        card_scroll = QScrollArea()
        card_scroll.setWidgetResizable(True)
        card_scroll.setFrameShape(QFrame.Shape.NoFrame)
        card_scroll.setObjectName("PageScroll")
        self._card_host = QWidget()
        self._card_host.setObjectName("ScrollContent")
        self._card_host.setAutoFillBackground(True)
        self._card_layout = QVBoxLayout(self._card_host)
        self._card_layout.setContentsMargins(24, 16, 24, 16)
        self._card_layout.setSpacing(12)
        card_scroll.setWidget(self._card_host)
        card_outer.addWidget(card_scroll, 1)
        mid.addWidget(self._card_holder, 1)
        root.addLayout(mid, 1)

        # Bottom nav — prev/next, bookmark/mark, finish
        self._bottom = QHBoxLayout()
        self._bottom.setContentsMargins(24, 16, 24, 16)
        self._prev = QPushButton("‹ Previous")
        self._prev.setObjectName("Secondary")
        self._prev.clicked.connect(self._go_prev)
        self._next = QPushButton("Next ›")
        self._next.setObjectName("Secondary")
        self._next.clicked.connect(self._go_next)
        self._bookmark_btn = QPushButton("☆ Bookmark")
        self._bookmark_btn.setObjectName("Secondary")
        self._bookmark_btn.clicked.connect(self._toggle_bookmark)
        self._mark_btn = QPushButton("Mark for review")
        self._mark_btn.setObjectName("Secondary")
        self._mark_btn.clicked.connect(self._toggle_mark)
        self._pause = QPushButton("Pause & Exit")
        self._pause.setObjectName("Secondary")
        self._pause.clicked.connect(self._pause_and_exit)
        self._finish = QPushButton("Finish Exam")
        self._finish.setObjectName("Primary")
        self._finish.clicked.connect(self._finish_exam)
        self._bottom.addWidget(self._prev)
        self._bottom.addWidget(self._next)
        self._bottom.addStretch()
        self._bottom.addWidget(self._bookmark_btn)
        self._bottom.addWidget(self._mark_btn)
        self._bottom.addWidget(self._pause)
        self._bottom.addWidget(self._finish)
        root.addLayout(self._bottom)

        self._grid_buttons: list[QPushButton] = []
        self._on_paused: Callable[..., Any] | None = None

    # -----/ Lifecycle /-----
    def start_exam(self, bank, mode: ExamMode = ExamMode.EXAM) -> None:
        """Start from a full bank (legacy / retake helper)."""
        from openboson.gui.engine import start_session

        session = start_session(bank, mode=mode)
        self.start_session(session)

    def start_session(
        self,
        session: ExamSession,
        *,
        start_timer: bool = True,
    ) -> None:
        """Start or resume from an existing session (blueprint exam)."""
        self._session = session
        self._active = True
        # Replace timer widget in place.
        old = self._timer
        old.stop()
        old.set_on_timeout(None)
        self._timer_host.removeWidget(old)
        old.deleteLater()
        limit = session.exam.time_limit_minutes
        self._timer = TimerBar(len(session.questions), limit_minutes=limit)
        self._timer.set_on_timeout(self._on_timeout)
        if session.remaining_seconds is not None:
            self._timer.set_remaining(session.remaining_seconds)
        self._timer_host.addWidget(self._timer, 1)
        self._build_grid()
        self._render_current()
        if start_timer and not session.is_paused():
            self._timer.start()
            save_active_session(session, remaining_seconds=self._timer.remaining_seconds())
        elif session.is_paused():
            self._timer.pause()
            save_active_session(session, remaining_seconds=self._timer.remaining_seconds())
        else:
            self._timer.pause()
            save_active_session(session, remaining_seconds=self._timer.remaining_seconds())

    def set_on_result(self, callback) -> None:
        self._on_result = callback

    def set_on_exit(self, callback) -> None:
        self._on_exit = callback

    def set_on_paused(self, callback) -> None:
        self._on_paused = callback

    def is_exam_active(self) -> bool:
        return (
            self._active
            and self._session is not None
            and not self._session.is_finished()
            and not self._session.is_paused()
        )

    def cleanup(self) -> None:
        """Stop the timer and clear callbacks so hidden timeouts cannot fire."""
        self._active = False
        self._timer.stop()
        self._timer.set_on_timeout(None)

    def _autosave(self) -> None:
        if self._session is None or self._session.is_finished():
            return
        save_active_session(self._session, remaining_seconds=self._timer.remaining_seconds())

    def _pause_and_exit(self) -> None:
        if self._session is None or self._session.is_finished():
            return
        remaining = self._timer.remaining_seconds()
        self._timer.pause()
        pause_session(self._session, remaining)
        self._active = False
        self._timer.set_on_timeout(None)
        if self._on_paused:
            self._on_paused(self._session)
        elif self._on_exit:
            self._on_exit()

    def _build_grid(self) -> None:
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        self._grid_buttons = []
        if self._session is None:
            return
        cols = 5
        for i in range(len(self._session.questions)):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(32, 28)
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _=False, idx=i: self._jump(idx))
            self._grid_layout.addWidget(btn, i // cols, i % cols)
            self._grid_buttons.append(btn)

    def _jump(self, index: int) -> None:
        if self._session is None:
            return
        self._session.goto(index)
        self._render_current()
        self._autosave()

    # -----/ Rendering /-----
    def _render_current(self) -> None:
        if self._session is None:
            return
        sess = self._session
        q = sess.current_question
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        presentation = _presentation_for(sess, q.id)
        card = QuestionCard(q, presentation=presentation)
        existing = sess.answers.get(q.id)
        if existing is not None:
            card.set_answer(existing.answer)
        card.answerChanged.connect(lambda ans, qid=q.id: self._store_answer(qid, ans))
        # Ordered lists emit an initial display order during construction, but
        # the signal was not connected yet. Persist that order after wiring so
        # next/back restores the same arrangement instead of reshuffling.
        if (
            existing is None
            and q.type == QuestionType.ORDERED_LIST
            and card.current_answer() is not None
        ):
            self._store_answer(q.id, card.current_answer())
        self._card_layout.addWidget(card)
        self._current_card = card

        self._qnum.setText(f"Question {sess.current_index + 1} / {len(sess.questions)}")
        self._timer.set_progress(sess.answered_count())
        self._update_bookmark_button()
        self._update_mark_button()
        self._prev.setEnabled(sess.current_index > 0)
        self._next.setEnabled(sess.current_index < len(sess.questions) - 1)
        self._refresh_grid_styles()

    def _refresh_grid_styles(self) -> None:
        if self._session is None:
            return
        for i, btn in enumerate(self._grid_buttons):
            q = self._session.questions[i]
            ua = self._session.answers.get(q.id)
            answered = ua is not None and ua.answer is not None
            bookmarked = q.id in self._session.bookmarked
            marked = q.id in self._session.marked_for_review
            current = i == self._session.current_index
            if current:
                btn.setStyleSheet("background: #1f6feb; color: white;")
            elif marked:
                btn.setStyleSheet("background: #9e6a03; color: white;")
            elif bookmarked:
                btn.setStyleSheet("background: #388bfd33;")
            elif answered:
                btn.setStyleSheet("background: #238636;")
            else:
                btn.setStyleSheet("")

    def _store_answer(self, qid: str, answer) -> None:
        if self._session is None:
            return
        # Exam mode: never grade until finish.
        self._session.submit_answer(qid, answer, grade_now=False)
        self._timer.set_progress(self._session.answered_count())
        self._refresh_grid_styles()
        self._autosave()

    def _toggle_bookmark(self) -> None:
        if self._session is None:
            return
        q = self._session.current_question
        self._session.toggle_bookmark(q.id)
        self._update_bookmark_button()
        self._refresh_grid_styles()
        self._autosave()

    def _toggle_mark(self) -> None:
        if self._session is None:
            return
        q = self._session.current_question
        self._session.toggle_mark_for_review(q.id)
        self._update_mark_button()
        self._refresh_grid_styles()
        self._autosave()

    def _update_bookmark_button(self) -> None:
        if self._session is None:
            return
        q = self._session.current_question
        if q.id in self._session.bookmarked:
            self._bookmark_btn.setText("★ Bookmarked")
        else:
            self._bookmark_btn.setText("☆ Bookmark")

    def _update_mark_button(self) -> None:
        if self._session is None:
            return
        q = self._session.current_question
        if q.id in self._session.marked_for_review:
            self._mark_btn.setText("Marked for review")
        else:
            self._mark_btn.setText("Mark for review")

    def _go_prev(self) -> None:
        if self._session is None:
            return
        if self._session.previous() is not None:
            self._render_current()
            self._autosave()

    def _go_next(self) -> None:
        if self._session is None:
            return
        if self._session.next() is not None:
            self._render_current()
            self._autosave()

    def _on_timeout(self) -> None:
        # Ignore timeouts from a timer that outlived the visible exam page.
        if not self._active or self._session is None or self._session.is_finished():
            return
        if not self.isVisible():
            self.cleanup()
            return
        self._finish_exam()

    def _finish_exam(self) -> None:
        if self._session is None or self._session.is_finished():
            return
        self.cleanup()
        result = finish_and_score(self._session)
        if self._on_result:
            self._on_result(self._session, result)

    # -----/ Test hooks /-----
    def current_question_id(self) -> str | None:
        if self._session is None:
            return None
        return self._session.current_question.id

    def answer_current(self, answer) -> None:
        if self._session is None:
            return
        qid = self._session.current_question.id
        self._store_answer(qid, answer)
