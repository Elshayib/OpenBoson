"""Teaching panel: explanation + per-choice rationales (practice / review only)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.bank_schema import Choice, MultipleChoiceAnswer, Question, SingleChoiceAnswer

_FALLBACK = "No explanation written for this item yet."


def correct_choice_ids(question: Question) -> set[str]:
    """Choice ids that grade as correct (empty for non-choice items)."""
    model = question.correct_answer_model
    if isinstance(model, SingleChoiceAnswer):
        return {model.answer}
    if isinstance(model, MultipleChoiceAnswer):
        return set(model.answers)
    return set()


def selected_choice_ids(answer: Any) -> set[str]:
    """Choice ids the candidate submitted, if the payload is choice-based."""
    if isinstance(answer, dict):
        if "answer" in answer and answer["answer"] is not None:
            return {str(answer["answer"])}
        if "answers" in answer and answer["answers"] is not None:
            return {str(a) for a in answer["answers"]}
    return set()


def format_choice_rationale(choice: Choice, *, why: str) -> str:
    """``Why right: a. 62 — /26 yields 62 usable hosts.``"""
    text = (choice.text or "").strip()
    rationale = (choice.rationale or "").strip()
    head = f"{choice.id}. {text}" if text else f"{choice.id}."
    if rationale:
        return f"{why}: {head} — {rationale}"
    return f"{why}: {head}"


class TeachingFeedback(QFrame):
    """Renders ``Question.explanation`` and per-choice ``rationale`` after grade."""

    def __init__(
        self,
        question: Question,
        *,
        is_correct: bool,
        selected: Any = None,
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
            right_ids = correct_choice_ids(question)
            picked_ids = selected_choice_ids(selected)
            for ch in question.choices:
                why = "Why right" if ch.id in right_ids else "Why wrong"
                line_text = format_choice_rationale(ch, why=why)
                if ch.id in picked_ids:
                    line_text += " (your answer)"
                line = QLabel(line_text)
                line.setWordWrap(True)
                line.setProperty("role", "muted")
                line.setObjectName("ChoiceRationale")
                v.addWidget(line)
