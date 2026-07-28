"""Exam review page — per-question explanation with correct vs user answer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.exsim.session import ExamSession


class ExamReviewPage(QWidget):
    """Lists questions with correct/user answers and explanations."""

    title = "Review"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(12)
        self._session: ExamSession | None = None

    def show_review(self, session: ExamSession) -> None:
        self._session = session
        self._clear()

        header = QLabel("Review Answers")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        # Filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))
        self._filter = QComboBox()
        self._filter.addItems(["All", "Incorrect", "Correct", "Bookmarked"])
        self._filter.currentTextChanged.connect(self._rebuild)
        filter_row.addWidget(self._filter)
        filter_row.addStretch()
        self._layout.addLayout(filter_row)

        self._items_holder = QVBoxLayout()
        self._layout.addLayout(self._items_holder)
        self._layout.addStretch()
        self._rebuild()

    def _rebuild(self) -> None:
        if self._session is None:
            return
        # Clear items holder
        while self._items_holder.count():
            item = self._items_holder.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        mode = self._filter.currentText()
        for q in self._session.questions:
            ua = self._session.answers.get(q.id)
            is_correct = bool(ua.is_correct) if ua is not None else False
            bookmarked = q.id in self._session.bookmarked
            if mode == "Incorrect" and is_correct:
                continue
            if mode == "Correct" and not is_correct:
                continue
            if mode == "Bookmarked" and not bookmarked:
                continue
            self._items_holder.addWidget(self._review_card(q, ua, is_correct))

    def _review_card(self, q, ua, is_correct: bool) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)

        top = QHBoxLayout()
        verdict = QLabel("✓ Correct" if is_correct else "✗ Incorrect")
        verdict.setStyleSheet("color: #3fb950;" if is_correct else "color: #f85149;")
        top.addWidget(verdict)
        top.addStretch()
        top.addWidget(QLabel(f"Topic {q.topic_code}"))
        v.addLayout(top)

        stem = QTextBrowser()
        stem.setMarkdown(q.stem.strip())
        stem.setMinimumHeight(50)
        stem.setFrameShape(QFrame.Shape.NoFrame)
        v.addWidget(stem)

        # Correct answer summary
        correct = q.correct_answer_model
        correct_text = self._summarize(correct)
        v.addWidget(QLabel(f"Correct: {correct_text}"))

        user_text = "(unanswered)"
        if ua is not None and ua.answer is not None:
            user_text = self._summarize_answer(ua.answer)
        v.addWidget(QLabel(f"Your answer: {user_text}"))

        if q.explanation:
            expl = QTextBrowser()
            expl.setMarkdown(q.explanation.strip())
            expl.setMinimumHeight(40)
            expl.setFrameShape(QFrame.Shape.NoFrame)
            v.addWidget(expl)
        return card

    @staticmethod
    def _summarize(correct) -> str:
        from openboson.bank_schema import (
            DragMatchAnswer,
            MultipleChoiceAnswer,
            OrderedListAnswer,
            SingleChoiceAnswer,
            SimAnswer,
        )

        if isinstance(correct, SingleChoiceAnswer):
            return f"answer {correct.answer}"
        if isinstance(correct, MultipleChoiceAnswer):
            return "answers " + ", ".join(correct.answers)
        if isinstance(correct, OrderedListAnswer):
            return "order " + " → ".join(correct.order)
        if isinstance(correct, DragMatchAnswer):
            return "pairs " + "; ".join(f"{p.left}={p.right}" for p in correct.pairs)
        if isinstance(correct, SimAnswer):
            return (correct.expected_config or "\n".join(correct.expected_commands or [])).strip()[:80]
        return ""

    @staticmethod
    def _summarize_answer(answer) -> str:
        if isinstance(answer, dict):
            if "answer" in answer:
                return f"answer {answer['answer']}"
            if "answers" in answer:
                return "answers " + ", ".join(answer["answers"])
            if "order" in answer:
                return "order " + " → ".join(answer["order"])
            if "pairs" in answer:
                return "pairs " + "; ".join(f"{p['left']}={p['right']}" for p in answer["pairs"])
            if "config" in answer:
                return answer["config"][:80]
        return str(answer)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
