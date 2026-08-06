"""NetSim lab list page — compact catalog table with filters."""

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
from openboson.netsim.lab_catalog import filter_labs, tier_badge
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
        self._scroll = ScrollHost(margins=(12, 12, 12, 12), spacing=8)
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
        tier = getattr(self, "_tier", None)
        search = getattr(self, "_search", None)
        prev_topic = topic.currentData() if topic is not None else "all"
        prev_diff = diff.currentData() if diff is not None else 0
        prev_tier = tier.currentData() if tier is not None else "all"
        prev_q = search.text() if search is not None else ""

        self._scroll.clear_content()

        header = QLabel("Network Labs")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)
        sub = QLabel(
            "Scenario labs are multi-device NetSim stories with behavioral verify. "
            "CLI drills are single-box practice."
        )
        sub.setProperty("role", "muted")
        sub.setWordWrap(True)
        self._layout.addWidget(sub)

        filters = QHBoxLayout()
        filters.setSpacing(6)
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

        self._tier = QComboBox()
        self._tier.addItem("All types", "all")
        self._tier.addItem("Scenario", "gold")
        self._tier.addItem("CLI drill", "drill")
        self._tier.addItem("Scale", "scale")
        xidx = max(0, self._tier.findData(prev_tier))
        self._tier.setCurrentIndex(xidx)
        self._tier.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(QLabel("Type"))
        filters.addWidget(self._tier)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search title, description, objectives…")
        self._search.setText(prev_q)
        self._search.textChanged.connect(self._apply_filters)
        filters.addWidget(self._search, 1)
        self._layout.addLayout(filters)

        self._count = QLabel("")
        self._count.setProperty("role", "muted")
        self._layout.addWidget(self._count)

        # Compact table header
        hdr = QFrame()
        hdr.setObjectName("TableRow")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(10, 6, 10, 6)
        hh.setSpacing(8)
        for text, stretch in (
            ("Lab", 3),
            ("Type", 1),
            ("Topic", 2),
            ("Difficulty", 1),
            ("", 0),
        ):
            lbl = QLabel(text)
            lbl.setProperty("role", "muted")
            if stretch:
                hh.addWidget(lbl, stretch)
            else:
                lbl.setFixedWidth(72)
                hh.addWidget(lbl)
        self._layout.addWidget(hdr)

        self._cards_host = QVBoxLayout()
        self._cards_host.setSpacing(4)
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
        tier = self._tier.currentData() if hasattr(self, "_tier") else "all"
        q = self._search.text() if hasattr(self, "_search") else ""
        filtered = filter_labs(
            self._all_labs,
            topic_code=None if topic in (None, "all") else str(topic),
            difficulty=None if not diff else int(diff),
            lab_tier=None if tier in (None, "all") else str(tier),
            q=q or None,
        )
        gold_n = sum(1 for lab in filtered if lab.lab_tier.value == "gold")
        self._count.setText(f"{len(filtered)} lab(s) · {gold_n} scenario(s)")
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
            self._cards_host.addWidget(self._lab_row(lab))

    def _lab_row(self, lab: LabBank) -> QFrame:
        """Dense table-style row (still a QFrame for existing tests)."""
        card = QFrame()
        card.setObjectName("Card")
        h = QHBoxLayout(card)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(8)

        title = QLabel(lab.title)
        title.setWordWrap(True)
        h.addWidget(title, 3)

        badge = QLabel(tier_badge(lab))
        badge.setProperty("role", "muted")
        h.addWidget(badge, 1)

        topic = QLabel(format_topic_label(lab.topic_code) if lab.topic_code else "—")
        topic.setProperty("role", "muted")
        topic.setWordWrap(True)
        h.addWidget(topic, 2)

        diff = QLabel("★" * lab.difficulty + "☆" * (5 - lab.difficulty))
        diff.setProperty("role", "muted")
        h.addWidget(diff, 1)

        start = QPushButton("Start")
        start.setObjectName("Primary")
        start.setFixedWidth(72)
        start.setToolTip(f"Start {lab.title}")
        start.clicked.connect(lambda _c=False, b=lab: self._start(b))
        h.addWidget(start)
        return card

    def _start(self, lab: LabBank) -> None:
        if self._lab_selected_callback:
            self._lab_selected_callback(lab)
