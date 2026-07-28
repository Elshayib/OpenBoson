"""NetSim lab list page — cards with title, topic, difficulty."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.gui.engine import load_available_labs


class LabListPage(QWidget):
    """Lists bundled lab banks and emits ``lab_selected`` to start one."""

    title = "Labs"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self._lab_selected_callback = None

    def set_on_lab_selected(self, callback) -> None:
        self._lab_selected_callback = callback

    def refresh(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        header = QLabel("Network Labs")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        labs = load_available_labs()
        if not labs:
            empty = QLabel("No labs found in data/demo_labs.")
            empty.setProperty("role", "muted")
            self._layout.addWidget(empty)
            return

        for lab in labs:
            self._layout.addWidget(self._lab_card(lab))
        self._layout.addStretch()

    def _lab_card(self, lab) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(8)

        title = QLabel(lab.title)
        title.setProperty("role", "h2")
        v.addWidget(title)

        meta = QLabel(
            f"Topic {lab.topic_code} • {len(lab.tasks)} tasks • "
            f"difficulty {'★' * lab.difficulty}{'☆' * (5 - lab.difficulty)}"
        )
        meta.setProperty("role", "muted")
        v.addWidget(meta)

        if lab.description:
            desc = QLabel(lab.description.strip())
            desc.setProperty("role", "muted")
            desc.setWordWrap(True)
            v.addWidget(desc)

        start = QPushButton("Start Lab")
        start.setObjectName("Primary")
        start.clicked.connect(lambda _c=False, b=lab: self._start(b))
        v.addWidget(start)
        return card

    def _start(self, lab) -> None:
        if self._lab_selected_callback:
            self._lab_selected_callback(lab)
