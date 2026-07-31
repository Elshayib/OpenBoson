"""Single-question practice page with Check + rich explanation."""

from __future__ import annotations

import contextlib

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson import stats_service
from openboson.bank_schema import (
    DragMatchAnswer,
    MultipleChoiceAnswer,
    OrderedListAnswer,
    Question,
    SimAnswer,
    SingleChoiceAnswer,
)
from openboson.exsim.scoring import grade_answer
from openboson.gui.widgets.question_card import QuestionCard


class PracticeQuestionPage(QWidget):
    """Answer one question, Check, then read a full explanation."""

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
        self._render_feedback(is_correct, answer)

    def _render_feedback(self, is_correct: bool, answer) -> None:
        q = self._question
        assert q is not None
        while self._feedback_holder.count():
            item = self._feedback_holder.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        panel = QFrame()
        panel.setObjectName("Card")
        v = QVBoxLayout(panel)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        banner = QLabel("Correct" if is_correct else "Incorrect")
        banner.setProperty("role", "h2")
        banner.setStyleSheet(
            "color: #3fb950;" if is_correct else "color: #f85149; font-weight: 700;"
        )
        v.addWidget(banner)

        v.addWidget(QLabel(f"Your answer: {self._summarize_answer(answer)}"))
        v.addWidget(QLabel(f"Correct answer: {self._summarize_correct(q)}"))

        if q.explanation:
            expl = QTextBrowser()
            expl.setMarkdown(q.explanation.strip())
            expl.setMinimumHeight(80)
            expl.setFrameShape(QFrame.Shape.NoFrame)
            expl.setObjectName("CardText")
            v.addWidget(expl)

        if q.choices:
            v.addWidget(QLabel("Choice rationales"))
            correct_ids: set[str] = set()
            model = q.correct_answer_model
            if isinstance(model, SingleChoiceAnswer):
                correct_ids = {model.answer}
            elif isinstance(model, MultipleChoiceAnswer):
                correct_ids = set(model.answers)
            user_ids: set[str] = set()
            if isinstance(answer, dict):
                if "answer" in answer:
                    user_ids = {str(answer["answer"])}
                elif "answers" in answer:
                    user_ids = set(answer["answers"])

            for choice in q.choices:
                bits = []
                if choice.id in correct_ids:
                    bits.append("correct")
                if choice.id in user_ids and choice.id not in correct_ids or choice.id in user_ids:
                    bits.append("your pick")
                title = f"{choice.id}. {choice.text}"
                if bits:
                    title += f" ({', '.join(bits)})"
                row = QLabel(title)
                row.setWordWrap(True)
                v.addWidget(row)
                if choice.rationale:
                    rat = QLabel(choice.rationale.strip())
                    rat.setWordWrap(True)
                    rat.setProperty("role", "muted")
                    v.addWidget(rat)

        if q.references:
            v.addWidget(QLabel("References"))
            for ref in q.references:
                r = QLabel(f"• {ref}")
                r.setWordWrap(True)
                r.setProperty("role", "muted")
                v.addWidget(r)

        self._feedback_holder.addWidget(panel)

    @staticmethod
    def _summarize_correct(q: Question) -> str:
        correct = q.correct_answer_model
        if isinstance(correct, SingleChoiceAnswer):
            if q.choices:
                for c in q.choices:
                    if c.id == correct.answer:
                        return f"{c.id}. {c.text}"
            return correct.answer
        if isinstance(correct, MultipleChoiceAnswer):
            return ", ".join(correct.answers)
        if isinstance(correct, OrderedListAnswer):
            return " → ".join(correct.order)
        if isinstance(correct, DragMatchAnswer):
            return "; ".join(f"{p.left} → {p.right}" for p in correct.pairs)
        if isinstance(correct, SimAnswer):
            cmds = correct.expected_commands or []
            return "; ".join(cmds) if cmds else (correct.expected_config or "")[:120]
        return ""

    @staticmethod
    def _summarize_answer(answer) -> str:
        if isinstance(answer, dict):
            if "answer" in answer:
                return str(answer["answer"])
            if "answers" in answer:
                return ", ".join(answer["answers"])
            if "order" in answer:
                return " → ".join(answer["order"])
            if "pairs" in answer:
                return "; ".join(f"{p['left']} → {p['right']}" for p in answer["pairs"])
            if "config" in answer:
                return (answer["config"] or "")[:120] or "(empty)"
        return str(answer) if answer is not None else "(unanswered)"
