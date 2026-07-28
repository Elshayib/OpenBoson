"""Exam list page — shows available banks as cards with mode selection."""

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

from openboson.bank_schema import ExamBank
from openboson.exsim.session import ExamMode
from openboson.gui.engine import load_available_banks


class ExamListPage(QWidget):
    """Lists bundled exam banks and emits ``exam_selected`` to start one."""

    title = "Exams"

    # Emitted with (ExamBank, ExamMode)
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self._exam_selected_callback = None

    def set_on_exam_selected(self, callback) -> None:
        self._exam_selected_callback = callback

    def refresh(self) -> None:
        self._layout.removeWidget(self._header() if False else QWidget())  # no-op guard
        self._rebuild()

    def _rebuild(self) -> None:
        # Clear existing widgets.
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        header = QLabel("Practice Exams")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        banks = load_available_banks()
        if not banks:
            empty = QLabel("No exam banks found in data/demo_banks.")
            empty.setProperty("role", "muted")
            self._layout.addWidget(empty)
            return

        for bank in banks:
            self._layout.addWidget(self._exam_card(bank))
        self._layout.addStretch()

    def _exam_card(self, bank: ExamBank) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(8)

        title = QLabel(f"{bank.title}  (v{bank.version})")
        title.setProperty("role", "h2")
        v.addWidget(title)

        meta = QLabel(
            f"Code {bank.code} • {len(bank.questions)} questions • "
            f"{bank.time_limit_minutes} min • pass {int(bank.pass_score * 100)}%"
        )
        meta.setProperty("role", "muted")
        v.addWidget(meta)

        if bank.description:
            desc = QLabel(bank.description.strip())
            desc.setProperty("role", "muted")
            desc.setWordWrap(True)
            v.addWidget(desc)

        # Mode selection
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        for mode in (ExamMode.STUDY, ExamMode.TIMED, ExamMode.CUSTOM):
            btn = QPushButton(mode.value.capitalize())
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _c=False, b=bank, m=mode: self._start(b, m))
            mode_row.addWidget(btn)
        mode_row.addStretch()
        v.addLayout(mode_row)

        # Primary action
        start = QPushButton("Start Timed Exam")
        start.setObjectName("Primary")
        start.clicked.connect(lambda _c=False, b=bank: self._start(b, ExamMode.TIMED))
        v.addWidget(start)
        return card

    def _start(self, bank: ExamBank, mode: ExamMode) -> None:
        if self._exam_selected_callback:
            self._exam_selected_callback(bank, mode)

    @staticmethod
    def _header() -> QLabel:
        return QLabel()
