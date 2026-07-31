"""Practice home — question library with filters and blueprint exam CTAs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import Question, QuestionType
from openboson.exsim.blueprint import InsufficientPoolError, list_blueprints
from openboson.gui import engine
from openboson.stats_service import QuestionStat, question_stats_map


class PracticePage(QWidget):
    """Question library + one-click CCNA / ENCOR exams."""

    title = "Practice"

    def __init__(self) -> None:
        super().__init__()
        self._on_practice_question = None
        self._on_start_exam = None
        self._stats: dict[str, QuestionStat] = {}
        self._all_questions: list[Question] = []
        self._topic_names: dict[str, str] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QLabel("Practice")
        header.setProperty("role", "h1")
        root.addWidget(header)

        # Exam CTAs
        exam_row = QHBoxLayout()
        for bp in list_blueprints():
            if bp.enabled:
                btn = QPushButton(f"Start {bp.code} {bp.version} Exam")
                btn.setObjectName("Primary")
                btn.setToolTip(
                    f"{bp.title} ({bp.version}) — {bp.question_count} questions, "
                    f"{bp.time_limit_minutes} min, pass {int(bp.pass_score * 100)}%"
                )
                btn.clicked.connect(lambda _=False, bid=bp.id: self._start_exam(bid))
            else:
                btn = QPushButton(
                    f"{bp.code} {bp.version} ({bp.coming_soon_label or 'Coming soon'})"
                )
                btn.setObjectName("Secondary")
                btn.setEnabled(False)
            exam_row.addWidget(btn)
        exam_row.addStretch()
        root.addLayout(exam_row)

        body = QHBoxLayout()
        body.setSpacing(16)

        # Filters
        filters = QFrame()
        filters.setObjectName("Card")
        filters.setFixedWidth(260)
        fl = QVBoxLayout(filters)
        fl.setContentsMargins(14, 14, 14, 14)
        fl.setSpacing(8)
        fl.addWidget(self._muted("Filters"))

        self._cert = QComboBox()
        self._cert.addItem("All certs", "all")
        self._cert.addItem("CCNA", "ccna")
        self._cert.addItem("CCNP", "ccnp")
        fl.addWidget(QLabel("Cert"))
        fl.addWidget(self._cert)

        self._topic = QComboBox()
        self._topic.addItem("All topics", "all")
        fl.addWidget(QLabel("Topic"))
        fl.addWidget(self._topic)

        self._difficulty = QComboBox()
        self._difficulty.addItem("All difficulties", 0)
        for d in range(1, 6):
            self._difficulty.addItem(f"{'★' * d}", d)
        fl.addWidget(QLabel("Difficulty"))
        fl.addWidget(self._difficulty)

        self._type = QComboBox()
        self._type.addItem("All types", "all")
        for qt in QuestionType:
            self._type.addItem(qt.value, qt.value)
        fl.addWidget(QLabel("Type"))
        fl.addWidget(self._type)

        self._seen = QComboBox()
        self._seen.addItem("All", "all")
        self._seen.addItem("Unseen", "unseen")
        self._seen.addItem("Missed", "missed")
        fl.addWidget(QLabel("History"))
        fl.addWidget(self._seen)

        self._sort = QComboBox()
        self._sort.addItem("Topic", "topic")
        self._sort.addItem("Difficulty", "difficulty")
        self._sort.addItem("Type", "type")
        self._sort.addItem("ID", "id")
        fl.addWidget(QLabel("Sort by"))
        fl.addWidget(self._sort)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search stem…")
        fl.addWidget(QLabel("Search"))
        fl.addWidget(self._search)

        fl.addStretch()
        body.addWidget(filters)

        # Question list
        right = QVBoxLayout()
        self._count_lbl = QLabel("")
        self._count_lbl.setProperty("role", "muted")
        right.addWidget(self._count_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_host = QWidget()
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._list_host)
        right.addWidget(scroll, 1)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        for widget in (
            self._cert,
            self._topic,
            self._difficulty,
            self._type,
            self._seen,
            self._sort,
        ):
            widget.currentIndexChanged.connect(self._on_filter_changed)
        self._search.textChanged.connect(self._apply_filters)

    def _on_filter_changed(self) -> None:
        # Cert changes which topics exist / which domain names apply.
        if self.sender() is self._cert:
            self._rebuild_topic_combo()
        self._apply_filters()

    def set_on_practice_question(self, callback) -> None:
        self._on_practice_question = callback

    def set_on_start_exam(self, callback) -> None:
        self._on_start_exam = callback

    def refresh(self) -> None:
        pool = engine.load_pool()
        self._all_questions = list(pool.questions)
        # Prefer exact topic names; also keep domain rollups from every bank file
        # so CCNA vs ENCOR domain titles both remain available.
        self._topic_names = {t.code: t.name for t in pool.topics}
        for bank in engine.load_available_banks():
            for t in bank.topics:
                # Keep first name per code from merge; still record alternates by bank code.
                self._topic_names.setdefault(t.code, t.name)
                self._topic_names[f"{bank.code}:{t.code}"] = t.name
        try:
            self._stats = question_stats_map()
        except Exception:
            self._stats = {}

        self._rebuild_topic_combo()
        self._apply_filters()

    def _rebuild_topic_combo(self) -> None:
        current = self._topic.currentData()
        cert = self._cert.currentData() if hasattr(self, "_cert") else "all"
        self._topic.blockSignals(True)
        self._topic.clear()
        self._topic.addItem("All topics", "all")
        codes = {q.topic_code for q in self._all_questions if cert == "all" or cert in q.cert_tags}
        for code in sorted(codes):
            self._topic.addItem(self._topic_label(code, cert), code)
        idx = max(0, self._topic.findData(current))
        self._topic.setCurrentIndex(idx)
        self._topic.blockSignals(False)

    def _topic_label(self, code: str, cert: str | None = None) -> str:
        """Return ``code — name`` for the filter, using domain rollup if needed."""
        names = getattr(self, "_topic_names", {}) or {}
        cert = (
            cert
            if cert is not None
            else (self._cert.currentData() if hasattr(self, "_cert") else "all")
        )
        name = names.get(code)
        prefix = code.split(".", 1)[0]
        rollup = f"{prefix}.0"
        if not name:
            # Prefer cert-specific domain title when pools share numeric codes.
            if cert == "ccna":
                name = names.get("pool-ccna:" + rollup) or names.get(rollup)
            elif cert == "ccnp":
                name = names.get("pool-encor:" + rollup) or names.get(rollup)
            else:
                name = names.get(rollup) or names.get(prefix)
        if not name:
            name = names.get(rollup) or names.get(prefix)
        if name:
            return f"{code} — {name}"
        return code

    def _start_exam(self, blueprint_id: str) -> None:
        if self._on_start_exam is None:
            return
        try:
            session = engine.start_blueprint_exam(blueprint_id)
        except InsufficientPoolError as exc:
            QMessageBox.warning(self, "Not enough questions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Cannot start exam", str(exc))
            return
        self._on_start_exam(session)

    def _apply_filters(self) -> None:
        cert = self._cert.currentData()
        topic = self._topic.currentData()
        diff = self._difficulty.currentData()
        qtype = self._type.currentData()
        seen = self._seen.currentData()
        sort_key = self._sort.currentData()
        search = self._search.text().strip().lower()

        filtered: list[Question] = []
        for q in self._all_questions:
            if cert != "all" and cert not in q.cert_tags:
                continue
            if topic != "all" and q.topic_code != topic:
                continue
            if diff and q.difficulty != diff:
                continue
            if qtype != "all" and q.type.value != qtype:
                continue
            st = self._stats.get(q.id)
            if seen == "unseen" and st is not None and st.seen > 0:
                continue
            if seen == "missed" and (st is None or st.misses == 0):
                continue
            if search and search not in q.stem.lower() and search not in q.id.lower():
                continue
            filtered.append(q)

        if sort_key == "topic":
            filtered.sort(key=lambda q: (q.topic_code, q.id))
        elif sort_key == "difficulty":
            filtered.sort(key=lambda q: (q.difficulty, q.id), reverse=True)
        elif sort_key == "type":
            filtered.sort(key=lambda q: (q.type.value, q.id))
        else:
            filtered.sort(key=lambda q: q.id)

        self._count_lbl.setText(f"{len(filtered)} question(s)")
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for q in filtered:
            self._list_layout.addWidget(self._row(q))
        self._list_layout.addStretch()

    def _row(self, q: Question) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

        top = QHBoxLayout()
        top.addWidget(QLabel(q.id))
        top.addWidget(self._muted(q.topic_code))
        top.addWidget(self._muted(q.type.value))
        top.addWidget(self._muted(" / ".join(t.upper() for t in q.cert_tags)))
        top.addStretch()
        top.addWidget(self._muted("★" * q.difficulty + "☆" * (5 - q.difficulty)))
        v.addLayout(top)

        stem = QLabel(q.stem.strip().splitlines()[0][:140])
        stem.setWordWrap(True)
        v.addWidget(stem)

        st = self._stats.get(q.id)
        if st is None or st.seen == 0:
            badge = self._muted("Unseen")
        elif st.misses:
            badge = self._muted(f"Missed {st.misses}× · seen {st.seen}")
        else:
            badge = self._muted(f"Seen {st.seen}×")
        v.addWidget(badge)

        card.mousePressEvent = lambda _e, question=q: self._open(question)  # type: ignore[method-assign]
        return card

    def _open(self, q: Question) -> None:
        if self._on_practice_question:
            self._on_practice_question(q)

    @staticmethod
    def _muted(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("role", "muted")
        return lbl
