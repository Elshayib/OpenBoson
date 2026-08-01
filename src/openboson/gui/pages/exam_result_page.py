"""Exam result page — score, pass/fail, per-domain breakdown, exports."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.exsim.export import export_text
from openboson.exsim.scoring import ExamResult
from openboson.gui.widgets.scroll_host import ScrollHost


class ExamResultPage(QWidget):
    """Shows the final score and lets the user review, export, or retake."""

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
        self._session = None
        self._result: ExamResult | None = None
        self._redacted_checked = False

    def set_on_review(self, cb) -> None:
        self._on_review = cb

    def set_on_retake(self, cb) -> None:
        self._on_retake = cb

    def show_result(self, session, result: ExamResult) -> None:
        self._session = session
        self._result = result
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

        export_row = QHBoxLayout()
        self._redacted = QCheckBox("Redacted (no answers)")
        self._redacted.setToolTip("Omit correct answers, rationales, and explanations")
        self._redacted.setChecked(self._redacted_checked)
        self._redacted.toggled.connect(self._on_redacted_toggled)
        export_row.addWidget(self._redacted)
        for label, fmt in (("JSON", "json"), ("CSV", "csv"), ("HTML", "html")):
            btn = QPushButton(f"Export {label}")
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _=False, f=fmt: self._export(f))
            export_row.addWidget(btn)
        print_btn = QPushButton("Print / PDF")
        print_btn.setObjectName("Secondary")
        print_btn.clicked.connect(self._print_pdf)
        export_row.addWidget(print_btn)
        export_row.addStretch()
        self._layout.addLayout(export_row)
        self._layout.addStretch()

    def _on_redacted_toggled(self, checked: bool) -> None:
        self._redacted_checked = bool(checked)

    def _is_redacted(self) -> bool:
        return bool(getattr(self, "_redacted", None) and self._redacted.isChecked())

    def _export(self, fmt: str) -> None:
        if self._session is None or self._result is None:
            return
        filters = {
            "json": "JSON (*.json)",
            "csv": "CSV (*.csv)",
            "html": "HTML (*.html)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {fmt.upper()}",
            f"openboson-exam.{fmt}",
            filters.get(fmt, "All files (*.*)"),
        )
        if not path:
            return
        try:
            text = export_text(
                self._session,
                fmt,  # type: ignore[arg-type]
                self._result,
                redacted=self._is_redacted(),
            )
            Path(path).write_text(text, encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export saved", f"Saved to:\n{path}")

    def _print_pdf(self) -> None:
        if self._session is None or self._result is None:
            return
        try:
            html_doc = export_text(
                self._session,
                "html",
                self._result,
                redacted=self._is_redacted(),
            )
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(html_doc)
            doc.print_(printer)
        except Exception as exc:
            QMessageBox.critical(self, "Print failed", str(exc))

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
