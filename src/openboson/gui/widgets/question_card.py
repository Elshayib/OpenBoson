"""Widgets for rendering a single exam question and capturing the answer.

``QuestionCard`` renders the stem in a QTextBrowser (Markdown-ish) and shows
the appropriate input control(s) depending on the question type:

    single_choice   -> QRadioButton group
    multiple_choice -> QCheckBox list
    drag_match      -> two-column pair assignment (left list -> right list)
    ordered_list    -> ordered QListWidget with up/down controls
    sim             -> terminal-like QPlainTextEdit for config + instructions
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import Question, QuestionType


class QuestionCard(QFrame):
    """Renders a question and emits ``answerChanged`` with the raw payload."""

    answerChanged = Signal(object)

    def __init__(self, question: Question) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._question = question
        self._current_answer: Any = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Topic + difficulty header
        header = QHBoxLayout()
        topic_lbl = QLabel(f"Topic {question.topic_code}")
        topic_lbl.setProperty("role", "muted")
        header.addWidget(topic_lbl)
        header.addStretch()
        diff_lbl = QLabel("★" * question.difficulty + "☆" * (5 - question.difficulty))
        diff_lbl.setProperty("role", "muted")
        header.addWidget(diff_lbl)
        layout.addLayout(header)

        # Stem
        stem = QTextBrowser()
        stem.setOpenExternalLinks(False)
        stem.setMarkdown(question.stem.strip())
        stem.setMinimumHeight(80)
        stem.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(stem)

        # Type-specific input
        self._build_input(question)
        layout.addWidget(self._input_container)

    # -----/ Builders /-----
    def _build_input(self, q: Question) -> None:
        if q.type == QuestionType.SINGLE_CHOICE:
            self._input_container = self._build_single_choice(q)
        elif q.type == QuestionType.MULTIPLE_CHOICE:
            self._input_container = self._build_multiple_choice(q)
        elif q.type == QuestionType.ORDERED_LIST:
            self._input_container = self._build_ordered_list(q)
        elif q.type == QuestionType.DRAG_MATCH:
            self._input_container = self._build_drag_match(q)
        elif q.type == QuestionType.SIM:
            self._input_container = self._build_sim(q)
        else:
            self._input_container = QLabel("Unsupported question type.")

    def _build_single_choice(self, q: Question) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)
        self._radio_group = QButtonGroup(w)
        self._radio_group.setExclusive(True)
        for choice in q.choices or []:
            rb = QRadioButton(choice.text)
            rb.setProperty("choice_id", choice.id)
            self._radio_group.addButton(rb)
            rb.toggled.connect(lambda _checked, b=rb: self._on_single(b))
            v.addWidget(rb)
        return w

    def _on_single(self, button: QRadioButton) -> None:
        if button.isChecked():
            cid = button.property("choice_id")
            self._current_answer = {"answer": cid}
            self.answerChanged.emit(self._current_answer)

    def _build_multiple_choice(self, q: Question) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)
        self._checks: list[QCheckBox] = []
        for choice in q.choices or []:
            cb = QCheckBox(choice.text)
            cb.setProperty("choice_id", choice.id)
            cb.stateChanged.connect(self._on_check)
            self._checks.append(cb)
            v.addWidget(cb)
        return w

    def _on_check(self, _state: int) -> None:
        selected = [cb.property("choice_id") for cb in self._checks if cb.isChecked()]
        self._current_answer = {"answers": selected}
        self.answerChanged.emit(self._current_answer)

    def _build_ordered_list(self, q: Question) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        self._order_list = QListWidget()
        self._order_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        items = list(q.ordered_items or [])
        for idx, item in enumerate(items):
            li = QListWidgetItem(f"{idx + 1}. {item}")
            li.setData(Qt.ItemDataRole.UserRole, item)
            self._order_list.addItem(li)
        v.addWidget(self._order_list)

        controls = QHBoxLayout()
        up = QPushButton("Up")
        up.setObjectName("Secondary")
        down = QPushButton("Down")
        down.setObjectName("Secondary")
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        controls.addWidget(up)
        controls.addWidget(down)
        controls.addStretch()
        v.addLayout(controls)
        return w

    def _move(self, delta: int) -> None:
        lst = self._order_list
        row = lst.currentRow()
        if row < 0 or 0 <= row + delta < lst.count():
            other = row + delta
            a = lst.takeItem(row)
            lst.insertItem(other, a)
            lst.setCurrentRow(other)
        self._emit_order()

    def _emit_order(self) -> None:
        order = [
            lst_item.data(Qt.ItemDataRole.UserRole)
            for i in range(self._order_list.count())
            if (lst_item := self._order_list.item(i)) is not None
        ]
        self._current_answer = {"order": order}
        self.answerChanged.emit(self._current_answer)

    def _build_drag_match(self, q: Question) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        note = QLabel("Match each item by pairing a left item with a right item.")
        note.setProperty("role", "muted")
        v.addWidget(note)
        self._pairs = q.drag_pairs or []
        self._match_rows: list[tuple[QListWidget, QListWidget]] = []
        for pair in self._pairs:
            row = QHBoxLayout()
            left = QListWidget()
            left.addItem(pair.left)
            left.setFixedHeight(28)
            right = QListWidget()
            right.addItem(pair.right)
            right.setFixedHeight(28)
            self._match_rows.append((left, right))
            row.addWidget(left)
            row.addWidget(right)
            v.addLayout(row)
        # We grade by checking that each left is paired with the correct right
        # during submission; the widget here just exposes the pairing order.
        self._current_answer = {
            "pairs": [{"left": p.left, "right": p.right} for p in self._pairs]
        }
        return w

    def _build_sim(self, q: Question) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        if q.sim is not None:
            instr = QTextBrowser()
            instr.setMarkdown(q.sim.instructions.strip())
            instr.setMinimumHeight(60)
            instr.setFrameShape(QFrame.Shape.NoFrame)
            v.addWidget(instr)
        term = QPlainTextEdit()
        term.setPlaceholderText("Paste or type the configuration / commands here...")
        term.setMinimumHeight(160)
        v.addWidget(term)
        term.textChanged.connect(lambda: self._on_sim(term))
        return w

    def _on_sim(self, editor: QPlainTextEdit) -> None:
        self._current_answer = {"config": editor.toPlainText()}
        self.answerChanged.emit(self._current_answer)

    # -----/ Public API /-----
    def current_answer(self) -> Any:
        return self._current_answer

    def set_answer(self, answer: Any) -> None:
        """Re-apply a previously stored answer (for navigation back)."""
        self._current_answer = answer
        if not answer:
            return
        q = self._question
        if q.type == QuestionType.SINGLE_CHOICE and isinstance(answer, dict):
            cid = answer.get("answer")
            for rb in self._radio_group.buttons():
                if rb.property("choice_id") == cid:
                    rb.setChecked(True)
        elif q.type == QuestionType.MULTIPLE_CHOICE and isinstance(answer, dict):
            selected = set(answer.get("answers", []))
            for cb in self._checks:
                cb.setChecked(cb.property("choice_id") in selected)
        elif q.type == QuestionType.ORDERED_LIST and isinstance(answer, dict):
            order = answer.get("order", [])
            self._order_list.clear()
            for idx, item in enumerate(order):
                li = QListWidgetItem(f"{idx + 1}. {item}")
                li.setData(Qt.ItemDataRole.UserRole, item)
                self._order_list.addItem(li)
        elif q.type == QuestionType.SIM and isinstance(answer, dict):
            # Sim editor is the last child widget's editor; find QPlainTextEdit.
            from PySide6.QtWidgets import QPlainTextEdit

            for child in self.findChildren(QPlainTextEdit):
                child.setPlainText(answer.get("config", ""))
                break
