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
from openboson.gui.widgets.scroll_host import ScrollHost


class LabListPage(QWidget):
    """Lists bundled lab banks and emits ``lab_selected`` to start one."""

    title = "Labs"

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._scroll = ScrollHost(margins=(24, 24, 24, 24), spacing=16)
        root.addWidget(self._scroll, 1)
        self._layout = self._scroll.content_layout
        self._lab_selected_callback = None

    def set_on_lab_selected(self, callback) -> None:
        self._lab_selected_callback = callback

    def refresh(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        self._scroll.clear_content()

        header = QLabel("Network Labs")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        labs = load_available_labs()
        if not labs:
            empty = QLabel("No labs found in data/demo_labs.")
            empty.setProperty("role", "muted")
            self._layout.addWidget(empty)
            self._layout.addStretch()
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
        title.setWordWrap(True)
        v.addWidget(title)

        meta = QLabel(
            f"Topic {lab.topic_code} • {len(lab.tasks)} tasks • "
            f"difficulty {'★' * lab.difficulty}{'☆' * (5 - lab.difficulty)}"
        )
        meta.setProperty("role", "muted")
        meta.setWordWrap(True)
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
