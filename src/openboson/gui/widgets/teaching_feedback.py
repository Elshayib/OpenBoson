"""Teaching panel: explanation + per-choice rationales (practice / review only)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import Question

_FALLBACK = "No explanation written for this item yet."


class TeachingFeedback(QFrame):
    """Renders ``Question.explanation`` and per-choice ``rationale`` after grade."""

    def __init__(
        self,
        question: Question,
        *,
        is_correct: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TeachingFeedback")
        self._is_correct = is_correct
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)

        title = QLabel("Explanation")
        title.setProperty("role", "h2")
        v.addWidget(title)

        body = QTextBrowser()
        body.setObjectName("ExplanationBody")
        body.setOpenExternalLinks(False)
        body.setFrameShape(QFrame.Shape.NoFrame)
        text = (question.explanation or "").strip() or _FALLBACK
        body.setMarkdown(text)
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        doc_h = int(body.document().size().height()) + 16
        body.setMinimumHeight(max(40, min(doc_h, 280)))
        v.addWidget(body)

        if question.choices:
            for ch in question.choices:
                if not (ch.rationale or "").strip():
                    continue
                line = QLabel(f"{ch.id}. {ch.rationale.strip()}")
                line.setWordWrap(True)
                line.setProperty("role", "muted")
                v.addWidget(line)
