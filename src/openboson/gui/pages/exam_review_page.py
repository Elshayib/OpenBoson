"""Exam review page — correct vs user answer plus teaching explanations."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.exsim.session import ExamSession
from openboson.gui.widgets.teaching_feedback import TeachingFeedback


class ExamReviewPage(QWidget):
    """Lists questions with answers, then explanation + per-choice rationale."""

    title = "Review"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(12)
        self._session: ExamSession | None = None
        self._scroll: QScrollArea | None = None
        self._items_host: QWidget | None = None
        self._items_holder: QVBoxLayout | None = None
        self._filter: QComboBox | None = None

    def show_review(self, session: ExamSession) -> None:
        self._session = session
        self._clear()

        header = QLabel("Review Answers")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))
        self._filter = QComboBox()
        self._filter.addItems(["All", "Incorrect", "Correct", "Bookmarked"])
        self._filter.currentTextChanged.connect(self._rebuild)
        filter_row.addWidget(self._filter)
        filter_row.addStretch()
        self._layout.addLayout(filter_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setObjectName("PageScroll")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._items_host = QWidget()
        self._items_host.setObjectName("ScrollContent")
        self._items_host.setAutoFillBackground(True)
        self._items_holder = QVBoxLayout(self._items_host)
        self._items_holder.setContentsMargins(0, 0, 0, 0)
        self._items_holder.setSpacing(12)
        self._scroll.setWidget(self._items_host)
        self._layout.addWidget(self._scroll, 1)
        self._rebuild()

    def scroll_area(self) -> QScrollArea | None:
        """Test / integration hook for the review scroll viewport."""
        return self._scroll

    def review_cards(self) -> list[QFrame]:
        if self._items_host is None:
            return []
        return [w for w in self._items_host.findChildren(QFrame) if w.objectName() == "Card"]

    def _rebuild(self) -> None:
        if self._session is None or self._items_holder is None:
            return
        while self._items_holder.count():
            item = self._items_holder.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        mode = self._filter.currentText() if self._filter is not None else "All"
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
        self._items_holder.addStretch()

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

        correct = q.correct_answer_model
        correct_lbl = QLabel(f"Correct: {self._summarize(q, correct)}")
        correct_lbl.setWordWrap(True)
        v.addWidget(correct_lbl)

        user_text = "(unanswered)"
        selected = None
        if ua is not None and ua.answer is not None:
            selected = ua.answer
            user_text = self._summarize_answer(q, ua.answer)
        user_lbl = QLabel(f"Your answer: {user_text}")
        user_lbl.setWordWrap(True)
        v.addWidget(user_lbl)
        v.addWidget(TeachingFeedback(q, is_correct=is_correct, selected=selected))
        return card

    @staticmethod
    def _choice_text(q, choice_id: str) -> str:
        if q.choices:
            for ch in q.choices:
                if ch.id == choice_id:
                    text = (ch.text or "").strip()
                    return text or str(choice_id)
        return str(choice_id)

    @staticmethod
    def _summarize(q, correct) -> str:
        from openboson.bank_schema import (
            DragMatchAnswer,
            MultipleChoiceAnswer,
            OrderedListAnswer,
            SimAnswer,
            SingleChoiceAnswer,
        )

        if isinstance(correct, SingleChoiceAnswer):
            return ExamReviewPage._choice_text(q, correct.answer)
        if isinstance(correct, MultipleChoiceAnswer):
            return ", ".join(ExamReviewPage._choice_text(q, cid) for cid in correct.answers)
        if isinstance(correct, OrderedListAnswer):
            return "order " + " → ".join(correct.order)
        if isinstance(correct, DragMatchAnswer):
            return "pairs " + "; ".join(f"{p.left}={p.right}" for p in correct.pairs)
        if isinstance(correct, SimAnswer):
            return (correct.expected_config or "\n".join(correct.expected_commands or [])).strip()[
                :80
            ]
        return ""

    @staticmethod
    def _summarize_answer(q, answer) -> str:
        if isinstance(answer, dict):
            if "answer" in answer:
                return ExamReviewPage._choice_text(q, str(answer["answer"]))
            if "answers" in answer:
                return ", ".join(
                    ExamReviewPage._choice_text(q, str(cid)) for cid in answer["answers"]
                )
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
            elif item.layout() is not None:
                nested = item.layout()
                while nested.count():
                    child = nested.takeAt(0)
                    if child.widget() is not None:
                        child.widget().deleteLater()
        self._scroll = None
        self._items_host = None
        self._items_holder = None
        self._filter = None
