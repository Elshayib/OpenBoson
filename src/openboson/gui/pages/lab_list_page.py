"""NetSim lab list page — catalog with topic / difficulty / text filters."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.exsim.objectives import format_topic_label
from openboson.gui.engine import load_available_labs
from openboson.gui.widgets.scroll_host import ScrollHost
from openboson.netsim.lab_catalog import filter_labs
from openboson.netsim.lab_schema import LabBank


class LabListPage(QWidget):
    """Lists bundled lab banks and emits ``lab_selected`` to start one."""

    title = "Labs"

    def __init__(self) -> None:
        super().__init__()
        self._lab_selected_callback = None
        self._all_labs: list[LabBank] = []
        self._built = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._scroll = ScrollHost(margins=(24, 24, 24, 24), spacing=16)
        root.addWidget(self._scroll, 1)
        self._layout = self._scroll.content_layout

    def set_on_lab_selected(self, callback) -> None:
        self._lab_selected_callback = callback

    def refresh(self, *, force: bool = False) -> None:
        labs = list(load_available_labs())
        fingerprint = tuple((lab.lab_id, lab.topic_code, lab.title) for lab in labs)
        if self._built and not force and fingerprint == getattr(self, "_labs_fp", None):
            return
        self._all_labs = labs
        self._labs_fp = fingerprint
        self._rebuild()
        self._built = True

    def _rebuild(self) -> None:
        # Preserve filter widget values across rebuilds when possible.
        topic = getattr(self, "_topic", None)
        diff = getattr(self, "_difficulty", None)
        search = getattr(self, "_search", None)
        prev_topic = topic.currentData() if topic is not None else "all"
        prev_diff = diff.currentData() if diff is not None else 0
        prev_q = search.text() if search is not None else ""

        self._scroll.clear_content()

        header = QLabel("Network Labs")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        filters = QHBoxLayout()
        self._topic = QComboBox()
        self._topic.addItem("All topics", "all")
        codes = sorted(
            {lab.topic_code for lab in self._all_labs if lab.topic_code},
            key=lambda c: [int(p) if p.isdigit() else p for p in c.split(".")],
        )
        for code in codes:
            self._topic.addItem(format_topic_label(code), code)
        tidx = max(0, self._topic.findData(prev_topic))
        self._topic.setCurrentIndex(tidx)
        self._topic.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(QLabel("Topic"))
        filters.addWidget(self._topic)

        self._difficulty = QComboBox()
        self._difficulty.addItem("All difficulties", 0)
        for d in range(1, 6):
            self._difficulty.addItem(f"{'★' * d}", d)
        didx = max(0, self._difficulty.findData(prev_diff))
        self._difficulty.setCurrentIndex(didx)
        self._difficulty.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(QLabel("Difficulty"))
        filters.addWidget(self._difficulty)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search title, description, objectives…")
        self._search.setText(prev_q)
        self._search.textChanged.connect(self._apply_filters)
        filters.addWidget(self._search, 1)
        self._layout.addLayout(filters)

        self._count = QLabel("")
        self._count.setProperty("role", "muted")
        self._layout.addWidget(self._count)

        self._cards_host = QVBoxLayout()
        self._layout.addLayout(self._cards_host)
        self._layout.addStretch()
        self._apply_filters()

    def _apply_filters(self, *_args: object) -> None:
        if not hasattr(self, "_cards_host"):
            return
        while self._cards_host.count():
            item = self._cards_host.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()

        topic = self._topic.currentData() if hasattr(self, "_topic") else "all"
        diff = self._difficulty.currentData() if hasattr(self, "_difficulty") else 0
        q = self._search.text() if hasattr(self, "_search") else ""
        filtered = filter_labs(
            self._all_labs,
            topic_code=None if topic in (None, "all") else str(topic),
            difficulty=None if not diff else int(diff),
            q=q or None,
        )
        self._count.setText(f"{len(filtered)} lab(s)")
        if not self._all_labs:
            empty = QLabel("No labs found in data/demo_labs.")
            empty.setProperty("role", "muted")
            self._cards_host.addWidget(empty)
            return
        if not filtered:
            empty = QLabel("No labs match these filters.")
            empty.setProperty("role", "muted")
            self._cards_host.addWidget(empty)
            return
        for lab in filtered:
            self._cards_host.addWidget(self._lab_card(lab))

    def _lab_card(self, lab: LabBank) -> QFrame:
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

    def _start(self, lab: LabBank) -> None:
        if self._lab_selected_callback:
            self._lab_selected_callback(lab)
