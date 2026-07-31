"""Exam result page — score, pass/fail, per-domain breakdown."""

from __future__ import annotations

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


class ExamResultPage(QWidget):
    """Shows the final score and lets the user review or retake."""

    title = "Result"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self._on_review = None
        self._on_retake = None

    def set_on_review(self, cb) -> None:
        self._on_review = cb

    def set_on_retake(self, cb) -> None:
        self._on_retake = cb

    def show_result(self, session, result: ExamResult) -> None:
        self._clear()
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
        name.setFixedWidth(220)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(d.percent * 100))
        pct = QLabel(f"{int(d.percent * 100)}%  ({d.correct}/{d.total})")
        pct.setFixedWidth(120)
        h.addWidget(name)
        h.addWidget(bar, 1)
        h.addWidget(pct)
        return w

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
