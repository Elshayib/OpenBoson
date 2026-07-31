"""Custom exam builder — filter the pool and start a fixed-length attempt."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from openboson.exsim.blueprint import InsufficientPoolError
from openboson.exsim.custom_exam import CustomExamSpec
from openboson.exsim.session import ExamSession
from openboson.gui import engine


class CustomExamPage(QWidget):
    """Build a custom exam: cert, topic, difficulty, history, length, time, seed."""

    title = "Custom Exam"

    def __init__(self) -> None:
        super().__init__()
        self._on_start: Callable[[ExamSession], Any] | None = None
        self._on_back: Callable[[], Any] | None = None
        self._editing_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Custom Exam")
        title.setProperty("role", "h1")
        header.addWidget(title)
        header.addStretch()
        self._back = QPushButton("‹ Back to Practice")
        self._back.setObjectName("Secondary")
        self._back.clicked.connect(self._go_back)
        header.addWidget(self._back)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form = QFormLayout(form_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self._title = QLineEdit("Custom Exam")
        form.addRow("Title", self._title)

        self._cert = QComboBox()
        self._cert.addItem("CCNA", "ccna")
        self._cert.addItem("CCNP (ENCOR)", "ccnp")
        self._cert.currentIndexChanged.connect(self._on_filters_changed)
        form.addRow("Cert", self._cert)

        self._topic = QComboBox()
        self._topic.addItem("All topics", "all")
        self._topic.currentIndexChanged.connect(self._on_filters_changed)
        form.addRow("Topic", self._topic)

        diff_row = QHBoxLayout()
        self._diff_checks: dict[int, QCheckBox] = {}
        for d in range(1, 6):
            cb = QCheckBox(str(d))
            cb.setChecked(False)
            cb.stateChanged.connect(self._on_filters_changed)
            self._diff_checks[d] = cb
            diff_row.addWidget(cb)
        diff_row.addStretch()
        form.addRow("Difficulty", diff_row)

        self._history = QComboBox()
        self._history.addItem("Any", "any")
        self._history.addItem("Missed only", "missed")
        self._history.addItem("Unseen only", "unseen")
        self._history.currentIndexChanged.connect(self._on_filters_changed)
        form.addRow("History", self._history)

        self._length = QSpinBox()
        self._length.setRange(1, 200)
        self._length.setValue(40)
        self._length.valueChanged.connect(self._on_filters_changed)
        form.addRow("Questions", self._length)

        self._time = QSpinBox()
        self._time.setRange(0, 480)
        self._time.setValue(60)
        self._time.setSuffix(" min")
        self._time.setSpecialValueText("Untimed")
        form.addRow("Time limit", self._time)

        self._seed = QSpinBox()
        self._seed.setRange(0, 2_147_483_647)
        self._seed.setValue(0)
        self._seed.setSpecialValueText("Random")
        form.addRow("Seed", self._seed)

        self._eligible = QLabel("")
        self._eligible.setProperty("role", "muted")
        form.addRow("Pool", self._eligible)

        actions = QHBoxLayout()
        self._start_btn = QPushButton("Start exam")
        self._start_btn.setObjectName("Primary")
        self._start_btn.clicked.connect(self._start)
        self._save_btn = QPushButton("Save preset")
        self._save_btn.setObjectName("Secondary")
        self._save_btn.clicked.connect(self._save_preset)
        actions.addWidget(self._start_btn)
        actions.addWidget(self._save_btn)
        actions.addStretch()
        form.addRow(actions)

        body.addWidget(form_card, 2)

        side = QFrame()
        side.setObjectName("Card")
        side.setMinimumWidth(220)
        side.setMaximumWidth(320)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 14, 14, 14)
        sl.addWidget(QLabel("Saved presets"))
        self._presets = QListWidget()
        self._presets.itemSelectionChanged.connect(self._on_preset_selected)
        sl.addWidget(self._presets, 1)
        preset_btns = QHBoxLayout()
        self._load_btn = QPushButton("Load")
        self._load_btn.setObjectName("Secondary")
        self._load_btn.clicked.connect(self._load_selected_preset)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("Secondary")
        self._delete_btn.clicked.connect(self._delete_selected_preset)
        preset_btns.addWidget(self._load_btn)
        preset_btns.addWidget(self._delete_btn)
        sl.addLayout(preset_btns)
        body.addWidget(side, 1)

        root.addLayout(body, 1)

    def set_on_start(self, callback: Callable[[ExamSession], Any]) -> None:
        self._on_start = callback

    def set_on_back(self, callback: Callable[[], Any]) -> None:
        self._on_back = callback

    def refresh(self) -> None:
        self._rebuild_topics()
        self._reload_presets()
        self._update_eligible()

    def _go_back(self) -> None:
        if self._on_back:
            self._on_back()

    def _rebuild_topics(self) -> None:
        current = self._topic.currentData()
        cert = self._cert.currentData()
        self._topic.blockSignals(True)
        self._topic.clear()
        self._topic.addItem("All topics", "all")
        try:
            pool = engine.load_pool()
            codes = sorted({q.topic_code for q in pool.questions if cert in q.cert_tags})
            for code in codes:
                self._topic.addItem(code, code)
        except Exception:
            pass
        idx = max(0, self._topic.findData(current))
        self._topic.setCurrentIndex(idx)
        self._topic.blockSignals(False)

    def _current_spec(self) -> CustomExamSpec:
        topic = self._topic.currentData()
        topic_codes = [] if topic in (None, "all") else [str(topic)]
        difficulties = [d for d, cb in self._diff_checks.items() if cb.isChecked()]
        seed_val = self._seed.value()
        return CustomExamSpec(
            title=self._title.text().strip() or "Custom Exam",
            cert=self._cert.currentData(),
            topic_codes=topic_codes,
            difficulties=difficulties,
            history=self._history.currentData(),
            question_count=self._length.value(),
            time_limit_minutes=self._time.value(),
            seed=None if seed_val == 0 else seed_val,
        )

    def _on_filters_changed(self, *_args: object) -> None:
        if self.sender() is self._cert:
            self._rebuild_topics()
        self._update_eligible()

    def _update_eligible(self) -> None:
        try:
            cov = engine.preview_custom_exam(self._current_spec())
            eligible = cov["eligible"]
            need = cov["requested"]
            self._eligible.setText(f"{eligible} eligible · need {need}")
            self._start_btn.setEnabled(eligible >= need)
        except Exception as exc:
            self._eligible.setText(f"Could not preview: {exc}")
            self._start_btn.setEnabled(False)

    def _start(self) -> None:
        if self._on_start is None:
            return
        try:
            session = engine.start_custom_exam(self._current_spec())
        except InsufficientPoolError as exc:
            QMessageBox.warning(self, "Not enough questions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Cannot start exam", str(exc))
            return
        if self._editing_id:
            session.custom_preset_id = self._editing_id
        self._on_start(session)

    def _save_preset(self) -> None:
        spec = self._current_spec()
        payload = spec.model_dump()
        if self._editing_id:
            payload["id"] = self._editing_id
        try:
            saved = engine.save_custom_preset(payload)
        except Exception as exc:
            QMessageBox.critical(self, "Cannot save preset", str(exc))
            return
        self._editing_id = saved.id
        self._reload_presets()
        QMessageBox.information(self, "Preset saved", f"Saved “{saved.title}”.")

    def _reload_presets(self) -> None:
        self._presets.clear()
        try:
            presets = engine.list_custom_presets()
        except Exception:
            return
        for p in presets:
            item = QListWidgetItem(f"{p.title} ({p.question_count}q)")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._presets.addItem(item)

    def _selected_preset_id(self) -> str | None:
        item = self._presets.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_preset_selected(self) -> None:
        pass

    def _load_selected_preset(self) -> None:
        preset_id = self._selected_preset_id()
        if not preset_id:
            return
        presets = {p.id: p for p in engine.list_custom_presets()}
        p = presets.get(preset_id)
        if p is None:
            return
        self._editing_id = p.id
        self._title.setText(p.title)
        idx = self._cert.findData(p.cert)
        if idx >= 0:
            self._cert.setCurrentIndex(idx)
        self._rebuild_topics()
        topic = p.topic_codes[0] if p.topic_codes else "all"
        tidx = self._topic.findData(topic)
        self._topic.setCurrentIndex(max(0, tidx))
        for d, cb in self._diff_checks.items():
            cb.setChecked(d in p.difficulties)
        hidx = self._history.findData(p.history)
        if hidx >= 0:
            self._history.setCurrentIndex(hidx)
        self._length.setValue(p.question_count)
        self._time.setValue(p.time_limit_minutes)
        self._seed.setValue(0 if p.seed is None else p.seed)
        self._update_eligible()

    def _delete_selected_preset(self) -> None:
        preset_id = self._selected_preset_id()
        if not preset_id:
            return
        engine.delete_custom_preset(preset_id)
        if self._editing_id == preset_id:
            self._editing_id = None
        self._reload_presets()
