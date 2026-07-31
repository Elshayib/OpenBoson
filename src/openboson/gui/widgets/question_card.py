"""Widgets for rendering a single exam question and capturing the answer.

``QuestionCard`` renders the stem in a QTextBrowser (Markdown-ish) and shows
the appropriate input control(s) depending on the question type:

    single_choice   -> QRadioButton group
    multiple_choice -> QCheckBox list
    drag_match      -> left slots + draggable right pool
    ordered_list    -> ordered QListWidget with InternalMove + up/down
    sim             -> terminal-like QPlainTextEdit for config + instructions
"""

from __future__ import annotations

import random
from typing import Any

from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import Question, QuestionType

_MIME_MATCH = "application/x-openboson-match"


class _MatchPoolList(QListWidget):
    """Source list of unmatched right-hand items."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMinimumHeight(120)
        self.setMaximumWidth(320)

    def startDrag(self, supportedActions: Qt.DropAction) -> None:  # noqa: N802
        item = self.currentItem()
        if item is None:
            return
        mime = QMimeData()
        mime.setData(_MIME_MATCH, item.text().encode("utf-8"))
        mime.setText(item.text())
        drag = QDrag(self)
        drag.setMimeData(mime)
        result = drag.exec(Qt.DropAction.MoveAction)
        if result == Qt.DropAction.MoveAction:
            row = self.row(item)
            self.takeItem(row)


class _MatchSlot(QFrame):
    """A drop target labelled with a left-side term."""

    changed = Signal()

    def __init__(self, left_label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.left_label = left_label
        self._right: str | None = None
        self.setAcceptDrops(True)
        self.setObjectName("MatchSlot")
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        self._left = QLabel(left_label)
        self._left.setMinimumWidth(140)
        self._right_lbl = QLabel("Drop match here")
        self._right_lbl.setProperty("role", "muted")
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("Secondary")
        self._clear_btn.setFixedWidth(28)
        self._clear_btn.clicked.connect(self.clear)
        self._clear_btn.setVisible(False)
        layout.addWidget(self._left)
        layout.addWidget(self._right_lbl, 1)
        layout.addWidget(self._clear_btn)
        self._set_idle_style()

    def right_value(self) -> str | None:
        return self._right

    def set_right(self, value: str | None) -> None:
        self._right = value
        if value:
            self._right_lbl.setText(value)
            self._right_lbl.setProperty("role", "")
            self._clear_btn.setVisible(True)
            self._set_filled_style()
        else:
            self._right_lbl.setText("Drop match here")
            self._right_lbl.setProperty("role", "muted")
            self._clear_btn.setVisible(False)
            self._set_idle_style()
        self._right_lbl.style().unpolish(self._right_lbl)
        self._right_lbl.style().polish(self._right_lbl)
        self.changed.emit()

    def clear(self) -> None:
        prev = self._right
        self.set_right(None)
        if prev is not None:
            # Parent card re-homes the item into the pool.
            parent = self.parent()
            while parent is not None and not hasattr(parent, "return_to_pool"):
                parent = parent.parent()
            if parent is not None and hasattr(parent, "return_to_pool"):
                parent.return_to_pool(prev)  # type: ignore[attr-defined]

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(_MIME_MATCH) or event.mimeData().hasText():
            event.acceptProposedAction()
            self._set_hover_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        if self._right:
            self._set_filled_style()
        else:
            self._set_idle_style()

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        text = None
        if mime.hasFormat(_MIME_MATCH):
            text = bytes(mime.data(_MIME_MATCH)).decode("utf-8")
        elif mime.hasText():
            text = mime.text()
        if not text:
            event.ignore()
            return
        # If slot already filled, return previous to pool.
        if self._right:
            prev = self._right
            parent = self.parent()
            while parent is not None and not hasattr(parent, "return_to_pool"):
                parent = parent.parent()
            if parent is not None and hasattr(parent, "return_to_pool"):
                parent.return_to_pool(prev)  # type: ignore[attr-defined]
        self.set_right(text)
        event.acceptProposedAction()

    def _set_idle_style(self) -> None:
        self.setStyleSheet(
            "#MatchSlot { border: 1px dashed #484f58; border-radius: 6px; background: #161b22; }"
        )

    def _set_hover_style(self) -> None:
        self.setStyleSheet(
            "#MatchSlot { border: 2px solid #58a6ff; border-radius: 6px; background: #1f2937; }"
        )

    def _set_filled_style(self) -> None:
        self.setStyleSheet(
            "#MatchSlot { border: 1px solid #3fb950; border-radius: 6px; background: #12261a; }"
        )


class _MatchWidget(QWidget):
    """Left slots + right pool for drag_match questions."""

    answerChanged = Signal(object)

    def __init__(self, pairs: list, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pairs = list(pairs)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Terms"))
        self._slots: list[_MatchSlot] = []
        for pair in self._pairs:
            slot = _MatchSlot(pair.left, self)
            slot.changed.connect(self._emit)
            self._slots.append(slot)
            left_col.addWidget(slot)
        left_col.addStretch()
        layout.addLayout(left_col, 2)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Match pool (drag onto a term)"))
        self._pool = _MatchPoolList()
        rights = [p.right for p in self._pairs]
        random.shuffle(rights)
        for text in rights:
            self._pool.addItem(text)
        right_col.addWidget(self._pool)
        layout.addLayout(right_col, 1)
        self._emit()

    def return_to_pool(self, text: str) -> None:
        self._pool.addItem(text)

    def _emit(self) -> None:
        pairs = []
        for slot in self._slots:
            if slot.right_value():
                pairs.append({"left": slot.left_label, "right": slot.right_value()})
        self.answerChanged.emit({"pairs": pairs})

    def set_pairs(self, pairs: list[dict[str, str]]) -> None:
        # Rebuild pool from all rights, then assign.
        all_rights = [p.right for p in self._pairs]
        assigned = {p["left"]: p["right"] for p in pairs if "left" in p and "right" in p}
        self._pool.clear()
        used: set[str] = set()
        for slot in self._slots:
            right = assigned.get(slot.left_label)
            # Avoid triggering return_to_pool on set.
            slot._right = None
            if right and right in all_rights and right not in used:
                slot.set_right(right)
                used.add(right)
            else:
                slot.set_right(None)
        for text in all_rights:
            if text not in used:
                self._pool.addItem(text)
        self._emit()

    def set_locked(self, locked: bool) -> None:
        self._pool.setDragEnabled(not locked)
        for slot in self._slots:
            slot.setAcceptDrops(not locked)
            slot._clear_btn.setEnabled(not locked)


class QuestionCard(QFrame):
    """Renders a question and emits ``answerChanged`` with the raw payload."""

    answerChanged = Signal(object)

    def __init__(self, question: Question) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._question = question
        self._current_answer: Any = None
        self._locked = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Topic + difficulty header
        header = QHBoxLayout()
        topic_lbl = QLabel(f"Topic {question.topic_code}")
        topic_lbl.setProperty("role", "muted")
        header.addWidget(topic_lbl)
        tags = ", ".join(t.upper() for t in question.cert_tags)
        cert_lbl = QLabel(tags)
        cert_lbl.setProperty("role", "muted")
        header.addWidget(cert_lbl)
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
        hint = QLabel("Drag items to reorder, or use Up / Down.")
        hint.setProperty("role", "muted")
        v.addWidget(hint)
        self._order_list = QListWidget()
        self._order_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._order_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._order_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._order_list.setDropIndicatorShown(True)
        self._order_list.setStyleSheet(
            "QListWidget::item:selected { background: #1f6feb; }"
            "QListWidget { outline: none; }"
        )
        items = list(q.ordered_items or [])
        random.shuffle(items)
        for idx, item in enumerate(items):
            li = QListWidgetItem(f"{idx + 1}. {item}")
            li.setData(Qt.ItemDataRole.UserRole, item)
            self._order_list.addItem(li)
        self._order_list.model().rowsMoved.connect(lambda *_a: self._renumber_and_emit())
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
        self._emit_order()
        return w

    def _move(self, delta: int) -> None:
        lst = self._order_list
        row = lst.currentRow()
        if row < 0:
            return
        other = row + delta
        if not (0 <= other < lst.count()):
            return
        a = lst.takeItem(row)
        lst.insertItem(other, a)
        lst.setCurrentRow(other)
        self._renumber_and_emit()

    def _renumber_and_emit(self) -> None:
        for i in range(self._order_list.count()):
            item = self._order_list.item(i)
            if item is None:
                continue
            raw = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"{i + 1}. {raw}")
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
        note = QLabel("Drag each match from the pool onto the correct term.")
        note.setProperty("role", "muted")
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(note)
        self._match_widget = _MatchWidget(q.drag_pairs or [])
        self._match_widget.answerChanged.connect(self._on_match)
        v.addWidget(self._match_widget)
        self._current_answer = {"pairs": []}
        return wrap

    def _on_match(self, payload: dict) -> None:
        self._current_answer = payload
        self.answerChanged.emit(self._current_answer)

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
        self._sim_editor = term
        return w

    def _on_sim(self, editor: QPlainTextEdit) -> None:
        self._current_answer = {"config": editor.toPlainText()}
        self.answerChanged.emit(self._current_answer)

    # -----/ Public API /-----
    def current_answer(self) -> Any:
        return self._current_answer

    def set_locked(self, locked: bool) -> None:
        """Disable further edits (after practice Check)."""
        self._locked = locked
        self._input_container.setEnabled(not locked)
        if hasattr(self, "_match_widget"):
            self._match_widget.set_locked(locked)

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
            self._emit_order()
        elif q.type == QuestionType.DRAG_MATCH and isinstance(answer, dict):
            self._match_widget.set_pairs(answer.get("pairs", []))
        elif q.type == QuestionType.SIM and isinstance(answer, dict):
            for child in self.findChildren(QPlainTextEdit):
                child.setPlainText(answer.get("config", ""))
                break
