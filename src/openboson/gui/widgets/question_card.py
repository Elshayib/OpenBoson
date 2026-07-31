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

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
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
from openboson.exsim.session import QuestionPresentation, build_question_presentation

_MIME_MATCH = "application/x-openboson-match"


def _normalize_drag_item(item: Any, fallback_id: str) -> dict[str, str]:
    """Normalize DragPair / DragItem / dict into ``{id, text}``."""
    if isinstance(item, dict):
        text = str(item.get("text") or item.get("right") or item.get("left") or "")
        return {"id": str(item.get("id") or fallback_id), "text": text}
    if hasattr(item, "id") and hasattr(item, "text"):
        return {"id": str(item.id), "text": str(item.text)}
    if hasattr(item, "right"):
        return {"id": fallback_id, "text": str(item.right)}
    if hasattr(item, "left"):
        return {"id": fallback_id, "text": str(item.left)}
    return {"id": fallback_id, "text": str(item)}


def _coerce_presentation(
    presentation: QuestionPresentation | dict[str, Any] | None,
    question: Question,
) -> dict[str, Any]:
    """Normalize session presentation to a dict; practice may reshuffle."""
    if isinstance(presentation, QuestionPresentation):
        return presentation.to_dict()
    if isinstance(presentation, dict) and presentation:
        return presentation
    return build_question_presentation(question).to_dict()


class _MatchPoolList(QListWidget):
    """Source list of unmatched right-hand items (opaque IDs in UserRole)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def startDrag(self, supportedActions: Qt.DropAction) -> None:  # noqa: N802
        item = self.currentItem()
        if item is None:
            return
        token_id = item.data(Qt.ItemDataRole.UserRole)
        if not token_id:
            return
        mime = QMimeData()
        mime.setData(_MIME_MATCH, str(token_id).encode("utf-8"))
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
        self._right_id: str | None = None
        self._right_text: str | None = None
        self.setAcceptDrops(True)
        self.setObjectName("MatchSlot")
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        self._left = QLabel(left_label)
        self._left.setMinimumWidth(100)
        self._left.setWordWrap(True)
        self._right_lbl = QLabel("Drop match here")
        self._right_lbl.setProperty("role", "muted")
        self._right_lbl.setWordWrap(True)
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
        return self._right_text

    def right_id(self) -> str | None:
        return self._right_id

    def set_right(self, token_id: str | None, text: str | None = None) -> None:
        self._right_id = token_id
        self._right_text = text if token_id else None
        if token_id and text:
            self._right_lbl.setText(text)
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
        prev_id = self._right_id
        prev_text = self._right_text
        self.set_right(None)
        if prev_id is not None and prev_text is not None:
            parent = self.parent()
            while parent is not None and not hasattr(parent, "return_to_pool"):
                parent = parent.parent()
            if parent is not None:
                return_to_pool = getattr(parent, "return_to_pool", None)
                if return_to_pool is not None:
                    return_to_pool(prev_id, prev_text)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(_MIME_MATCH) or event.mimeData().hasText():
            event.acceptProposedAction()
            self._set_hover_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        if self._right_id:
            self._set_filled_style()
        else:
            self._set_idle_style()

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        token_id = None
        text = None
        if mime.hasFormat(_MIME_MATCH):
            token_id = bytes(mime.data(_MIME_MATCH)).decode("utf-8")
            text = mime.text() if mime.hasText() else None
            parent = self.parent()
            while parent is not None and not hasattr(parent, "token_text"):
                parent = parent.parent()
            if parent is not None:
                token_text = getattr(parent, "token_text", None)
                if token_text is not None:
                    resolved = token_text(token_id)
                    if resolved is not None:
                        text = resolved
        elif mime.hasText():
            text = mime.text()
            token_id = text  # legacy fallback
        if not token_id or not text:
            event.ignore()
            return
        if self._right_id and self._right_text:
            prev_id, prev_text = self._right_id, self._right_text
            parent = self.parent()
            while parent is not None and not hasattr(parent, "return_to_pool"):
                parent = parent.parent()
            if parent is not None:
                return_to_pool = getattr(parent, "return_to_pool", None)
                if return_to_pool is not None:
                    return_to_pool(prev_id, prev_text)
        self.set_right(token_id, text)
        event.acceptProposedAction()

    def _set_idle_style(self) -> None:
        self._apply_match_state("idle")

    def _set_hover_style(self) -> None:
        self._apply_match_state("hover")

    def _set_filled_style(self) -> None:
        self._apply_match_state("filled")

    def _apply_match_state(self, state: str) -> None:
        """Drive MatchSlot chrome from theme QSS via ``matchState`` property."""
        self.setProperty("matchState", state)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()


class _MatchWidget(QWidget):
    """Left slots + right pool for drag_match questions.

    Left and right collections are independent (no canonical pairing).
    Each right-side token has an opaque ID so duplicate display strings
    (e.g. two ``Server → Client`` values) restore and edit independently.
    Answer payloads still use left/right display text for grading.
    """

    answerChanged = Signal(object)

    def __init__(
        self,
        left_items: list[dict[str, str]] | list,
        right_items: list[dict[str, str]] | list,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # Normalize to {id, text} dicts.
        self._left_items = [_normalize_drag_item(x, f"L{i}") for i, x in enumerate(left_items)]
        self._right_items = [_normalize_drag_item(x, f"R{i}") for i, x in enumerate(right_items)]
        self._tokens: dict[str, str] = {d["id"]: d["text"] for d in self._right_items}
        self._token_ids: list[str] = [d["id"] for d in self._right_items]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Terms"))
        self._slots: list[_MatchSlot] = []
        self._combos: list[QComboBox] = []
        for item in self._left_items:
            slot = _MatchSlot(item["text"], self)
            slot.changed.connect(self._on_slot_changed)
            self._slots.append(slot)
            left_col.addWidget(slot)

            combo = QComboBox()
            combo.setAccessibleName(f"Keyboard match for {item['text']}")
            combo.setToolTip("Keyboard alternative to dragging")
            combo.currentIndexChanged.connect(self._on_combo_changed)
            self._combos.append(combo)
            left_col.addWidget(combo)
        left_col.addStretch()
        layout.addLayout(left_col, 2)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Match pool (drag onto a term, or use the lists)"))
        self._pool = _MatchPoolList()
        self._pool.setAccessibleName("Match pool")
        for tid in self._token_ids:
            self._add_pool_item(tid)
        right_col.addWidget(self._pool)
        layout.addLayout(right_col, 1)
        self._rebuild_combos()
        self._emit()

    def token_text(self, token_id: str) -> str | None:
        return self._tokens.get(token_id)

    def _add_pool_item(self, token_id: str) -> None:
        text = self._tokens[token_id]
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, token_id)
        self._pool.addItem(item)

    def return_to_pool(self, token_id: str, text: str | None = None) -> None:
        if token_id not in self._tokens and text is not None:
            for tid, t in self._tokens.items():
                if t == text and not self._token_in_use(tid):
                    token_id = tid
                    break
            else:
                return
        if token_id in self._tokens:
            self._add_pool_item(token_id)
        self._rebuild_combos()

    def _token_in_use(self, token_id: str) -> bool:
        for slot in self._slots:
            if slot.right_id() == token_id:
                return True
        for i in range(self._pool.count()):
            item = self._pool.item(i)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == token_id:
                return True
        return False

    def _free_token_ids(self, *, keep_for_slot: int | None = None) -> list[str]:
        used = {
            slot.right_id()
            for i, slot in enumerate(self._slots)
            if slot.right_id() and i != keep_for_slot
        }
        return [tid for tid in self._token_ids if tid not in used]

    def _rebuild_combos(self) -> None:
        for i, combo in enumerate(self._combos):
            combo.blockSignals(True)
            current = self._slots[i].right_id()
            combo.clear()
            combo.addItem("(unmatched)", None)
            for tid in self._free_token_ids(keep_for_slot=i):
                combo.addItem(self._tokens[tid], tid)
            if current is not None:
                idx = combo.findData(current)
                if idx < 0:
                    combo.addItem(self._tokens[current], current)
                    idx = combo.findData(current)
                combo.setCurrentIndex(max(0, idx))
            else:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _on_slot_changed(self) -> None:
        self._rebuild_combos()
        self._emit()

    def _on_combo_changed(self) -> None:
        sender = self.sender()
        if not isinstance(sender, QComboBox):
            return
        try:
            idx = self._combos.index(sender)
        except ValueError:
            return
        token_id = sender.currentData()
        slot = self._slots[idx]
        previous = slot.right_id()
        if (
            previous
            and previous != token_id
            and previous
            not in {s.right_id() for j, s in enumerate(self._slots) if j != idx and s.right_id()}
        ):
            self._add_pool_item(previous)
        if token_id is None:
            slot.set_right(None)
        else:
            # Remove from pool if present.
            for i in range(self._pool.count()):
                item = self._pool.item(i)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == token_id:
                    self._pool.takeItem(i)
                    break
            # Clear other slots that held this token.
            for j, other in enumerate(self._slots):
                if j != idx and other.right_id() == token_id:
                    other.set_right(None)
            slot.set_right(token_id, self._tokens[token_id])
        self._rebuild_combos()
        self._emit()

    def _emit(self) -> None:
        pairs = []
        for slot in self._slots:
            if slot.right_value():
                pairs.append({"left": slot.left_label, "right": slot.right_value()})
        self.answerChanged.emit({"pairs": pairs})

    def set_pairs(self, pairs: list[dict[str, str]]) -> None:
        """Restore matches by consuming opaque tokens (supports duplicate rights)."""
        assigned = {p["left"]: p["right"] for p in pairs if "left" in p and "right" in p}
        available: dict[str, list[str]] = {}
        for tid, text in self._tokens.items():
            available.setdefault(text, []).append(tid)

        self._pool.clear()
        used_ids: set[str] = set()
        for slot in self._slots:
            slot._right_id = None
            slot._right_text = None
            right_text = assigned.get(slot.left_label)
            chosen: str | None = None
            if right_text is not None:
                bucket = available.get(right_text) or []
                if bucket:
                    chosen = bucket.pop(0)
            if chosen is not None:
                used_ids.add(chosen)
                slot.set_right(chosen, self._tokens[chosen])
            else:
                slot.set_right(None)

        for tid in self._token_ids:
            if tid not in used_ids:
                self._add_pool_item(tid)
        self._rebuild_combos()
        self._emit()

    def set_locked(self, locked: bool) -> None:
        self._pool.setDragEnabled(not locked)
        for slot in self._slots:
            slot.setAcceptDrops(not locked)
            slot._clear_btn.setEnabled(not locked)
        for combo in self._combos:
            combo.setEnabled(not locked)


class QuestionCard(QFrame):
    """Renders a question and emits ``answerChanged`` with the raw payload."""

    answerChanged = Signal(object)

    def __init__(
        self,
        question: Question,
        presentation: QuestionPresentation | dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._question = question
        self._presentation = _coerce_presentation(presentation, question)
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

        # Stem — transparent so it matches the Card surface in both themes
        stem = QTextBrowser()
        stem.setOpenExternalLinks(False)
        stem.setMarkdown(question.stem.strip())
        stem.setFrameShape(QFrame.Shape.NoFrame)
        stem.setObjectName("CardText")
        stem.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        doc_h = int(stem.document().size().height()) + 20
        stem.setMinimumHeight(max(60, min(doc_h, 360)))
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

    def _choice_order(self, q: Question) -> list:
        """Choice list; prefer session presentation order when provided by engine."""
        choices = list(q.choices or [])
        order = self._presentation.get("choice_ids")
        if order and choices:
            by_id = {c.id: c for c in choices}
            ordered = [by_id[cid] for cid in order if cid in by_id]
            if len(ordered) == len(choices):
                return ordered
        return choices

    def _build_single_choice(self, q: Question) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)
        self._radio_group = QButtonGroup(w)
        self._radio_group.setExclusive(True)
        for choice in self._choice_order(q):
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
        for choice in self._choice_order(q):
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
        self._order_list.setStyleSheet("QListWidget { outline: none; }")
        items = list(q.ordered_items or [])
        # Prefer engine presentation order when available (stable across nav).
        presented = self._presentation.get("ordered_items")
        if presented is not None:
            items = list(presented)
        else:
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
        # Engine contract: left_items / right_items via presentation.to_dict().
        left_items = self._presentation.get("left_items")
        right_items = self._presentation.get("right_items")
        if not left_items or not right_items:
            # Legacy alias fallback (pre-contract presentation dicts).
            left_items = self._presentation.get("drag_left") or left_items
            right_items = self._presentation.get("drag_right") or right_items
        if not left_items or not right_items:
            # Last resort: split authored pairs and shuffle independently.
            pairs = list(q.drag_pairs or [])
            left_items = [{"id": f"L{i}", "text": p.left} for i, p in enumerate(pairs)]
            right_items = [{"id": f"R{i}", "text": p.right} for i, p in enumerate(pairs)]
            random.shuffle(left_items)
            random.shuffle(right_items)
        self._match_widget = _MatchWidget(left_items, right_items)
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
