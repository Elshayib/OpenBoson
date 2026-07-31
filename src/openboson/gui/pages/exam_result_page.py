"""Exam result page — score, pass/fail, per-domain breakdown."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.exsim.scoring import ExamResult
from openboson.gui.widgets.scroll_host import ScrollHost


class ExamResultPage(QWidget):
    """Shows the final score and lets the user review or retake."""

    title = "Result"

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._scroll = ScrollHost(margins=(24, 24, 24, 24), spacing=16)
        root.addWidget(self._scroll, 1)
        self._layout = self._scroll.content_layout
        self._on_review = None
        self._on_retake = None

    def set_on_review(self, cb) -> None:
        self._on_review = cb

    def set_on_retake(self, cb) -> None:
        self._on_retake = cb

    def show_result(self, session, result: ExamResult) -> None:
        self._scroll.clear_content()
        header = QLabel("Exam Complete")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        # Pass / fail banner
        banner = QFrame()
        banner.setObjectName("Card")
        bl = QVBoxLayout(banner)
        verdict = QLabel("PASSED" if result.passed else "FAILED")
        verdict.setProperty("role", "h1")
        verdict.setStyleSheet("color: #3fb950;" if result.passed else "color: #f85149;")
        bl.addWidget(verdict)
        score = QLabel(
            f"Score: {result.score_percent:.1f}%  (pass mark {int(result.passing_score * 100)}%)"
        )
        score.setProperty("role", "muted")
        score.setWordWrap(True)
        bl.addWidget(score)
        self._layout.addWidget(banner)

        # Per-domain breakdown
        domains = QLabel("Domain Breakdown")
        domains.setProperty("role", "h2")
        self._layout.addWidget(domains)
        for prefix, d in result.domain_breakdown.items():
            self._layout.addWidget(self._domain_row(prefix, d))

        # Actions
        actions = QHBoxLayout()
        review = QPushButton("Review Answers")
        review.setObjectName("Primary")
        review.clicked.connect(lambda: self._on_review and self._on_review(session))
        retake = QPushButton("Retake Exam")
        retake.setObjectName("Secondary")
        retake.clicked.connect(lambda: self._on_retake and self._on_retake(session))
        actions.addWidget(review)
        actions.addWidget(retake)
        actions.addStretch()
        self._layout.addLayout(actions)
        self._layout.addStretch()

    def _domain_row(self, prefix: str, d) -> QWidget:
        w = QFrame()
        w.setObjectName("Card")
        h = QHBoxLayout(w)
        h.setContentsMargins(14, 10, 14, 10)
        name = QLabel(f"{prefix}  ({int(d.weight * 100)}% of exam)")
        name.setMinimumWidth(100)
        name.setWordWrap(True)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(d.percent * 100))
        pct = QLabel(f"{int(d.percent * 100)}%  ({d.correct}/{d.total})")
        pct.setMinimumWidth(80)
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(name, 2)
        h.addWidget(bar, 3)
        h.addWidget(pct)
        return w
