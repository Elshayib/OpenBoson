"""NetSim lab result page — per-task pass/fail + overall score."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.netsim.session import LabResult, LabSession


class LabResultPage(QWidget):
    """Shows the final lab score and per-task breakdown."""

    title = "Lab Result"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self._on_retake = None

    def set_on_retake(self, cb) -> None:
        self._on_retake = cb

    def show_result(self, session: LabSession, result: LabResult) -> None:
        self._clear()
        header = QLabel("Lab Complete")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        banner = QFrame()
        banner.setObjectName("Card")
        bl = QVBoxLayout(banner)
        verdict = QLabel(
            "ALL TASKS PASSED" if result.passed_tasks == result.total_tasks
            else f"{result.passed_tasks} / {result.total_tasks} TASKS PASSED"
        )
        verdict.setProperty("role", "h1")
        verdict.setStyleSheet(
            "color: #3fb950;" if result.passed_tasks == result.total_tasks
            else "color: #f85149;"
        )
        bl.addWidget(verdict)
        score = QLabel(f"Score: {result.score_percent:.0f}%")
        score.setProperty("role", "muted")
        bl.addWidget(score)
        self._layout.addWidget(banner)

        # Per-task
        tasks_hdr = QLabel("Tasks")
        tasks_hdr.setProperty("role", "h2")
        self._layout.addWidget(tasks_hdr)
        for tid, g in result.task_grades.items():
            self._layout.addWidget(self._task_row(tid, g))

        actions = QHBoxLayout()
        retake = QPushButton("Retake Lab")
        retake.setObjectName("Secondary")
        retake.clicked.connect(lambda: self._on_retake and self._on_retake(session))
        actions.addWidget(retake)
        actions.addStretch()
        self._layout.addLayout(actions)
        self._layout.addStretch()

    def _task_row(self, tid: str, g) -> QWidget:
        w = QFrame()
        w.setObjectName("Card")
        h = QHBoxLayout(w)
        h.setContentsMargins(14, 10, 14, 10)
        mark = "✓" if g.is_correct else "✗"
        label = QLabel(f"{mark} {tid}")
        label.setStyleSheet("color: #3fb950;" if g.is_correct else "color: #f85149;")
        label.setFixedWidth(120)
        fb = QLabel(g.feedback)
        fb.setProperty("role", "muted")
        fb.setWordWrap(True)
        h.addWidget(label)
        h.addWidget(fb, 1)
        return w

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
