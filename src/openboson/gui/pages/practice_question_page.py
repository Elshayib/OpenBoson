"""Single-question practice page with Check (correct / incorrect only)."""

from __future__ import annotations

import contextlib

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from openboson import stats_service
from openboson.bank_schema import Question
from openboson.exsim.scoring import grade_answer
from openboson.gui.widgets.question_card import QuestionCard


class PracticeQuestionPage(QWidget):
    """Answer one question and Check for correct / incorrect only."""

    title = "Practice Question"

    def __init__(self) -> None:
        super().__init__()
        self._question: Question | None = None
        self._on_back = None
        self._card: QuestionCard | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(24, 16, 24, 8)
        self._back = QPushButton("‹ Back to library")
        self._back.setObjectName("Secondary")
        self._back.clicked.connect(self._go_back)
        top.addWidget(self._back)
        top.addStretch()
        self._check = QPushButton("Check Answer")
        self._check.setObjectName("Primary")
        self._check.clicked.connect(self._check_answer)
        top.addWidget(self._check)
        root.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("PageScroll")
        self._host = QWidget()
        self._host.setObjectName("ScrollContent")
        self._host.setAutoFillBackground(True)
        self._host_layout = QVBoxLayout(self._host)
        self._host_layout.setContentsMargins(24, 8, 24, 24)
        self._host_layout.setSpacing(16)
        scroll.setWidget(self._host)
        root.addWidget(scroll, 1)

    def set_on_back(self, callback) -> None:
        self._on_back = callback

    def show_question(self, question: Question) -> None:
        self._question = question
        self._clear_host()
        self._check.setEnabled(True)
        self._check.setVisible(True)
        self._card = QuestionCard(question)
        self._host_layout.addWidget(self._card)
        self._feedback_holder = QVBoxLayout()
        self._host_layout.addLayout(self._feedback_holder)
        self._host_layout.addStretch()

    def _clear_host(self) -> None:
        while self._host_layout.count():
            item = self._host_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _go_back(self) -> None:
        if self._on_back:
            self._on_back()

    def _check_answer(self) -> None:
        if self._question is None or self._card is None:
            return
        answer = self._card.current_answer()
        if answer is None:
            return
        is_correct = grade_answer(self._question, answer)
        with contextlib.suppress(Exception):
            stats_service.save_practice_attempt(self._question.id, is_correct)
        self._card.set_locked(True)
        self._check.setEnabled(False)
        self._render_feedback(is_correct)

    def _render_feedback(self, is_correct: bool) -> None:
        while self._feedback_holder.count():
            item = self._feedback_holder.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        panel = QFrame()
        panel.setObjectName("Card")
        v = QVBoxLayout(panel)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(0)

        banner = QLabel("Correct" if is_correct else "Incorrect")
        banner.setProperty("role", "h2")
        banner.setStyleSheet(
            "color: #3fb950;" if is_correct else "color: #f85149; font-weight: 700;"
        )
        v.addWidget(banner)
        self._feedback_holder.addWidget(panel)
