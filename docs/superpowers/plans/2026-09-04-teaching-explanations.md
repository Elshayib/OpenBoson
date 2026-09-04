# Teaching Explanations Implementation Plan

> **Status: DONE** on `master` (`TeachingFeedback`, exam silent, tests in
> `tests/gui/test_exam_flow.py`). Do not re-implement.

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development.
> Parallel-safe with study-loop / DHCP / content / presence if you only touch
> the files listed below.

**Goal:** Practice Check and exam review teach like Boson ExSim study/review
mode: show `explanation` and per-choice `rationale`. Timed exam session stays
silent.

**Architecture:** Read fields already on `Question` / `Choice` in
`bank_schema.py`. New widget `gui/widgets/teaching_feedback.py` renders
markdown explanation + rationale list. Practice Check uses it after grade.
Exam review uses it on each card. `ExamSessionPage` must **not** show it.
Redacted score export continues to omit explanations.

**Tech Stack:** PySide6, pytest-qt, existing Markdown QTextBrowser.

---

### Task 1: Widget + practice Check

**Files:**
- Create: `src/openboson/gui/widgets/teaching_feedback.py`
- Modify: `src/openboson/gui/pages/practice_question_page.py`
- Modify: `tests/gui/test_exam_flow.py` (`test_practice_question_check_shows_feedback`)

- [ ] **Step 1: Write failing GUI test**

Update `test_practice_question_check_shows_feedback` so that after a correct
Check, labels/text include teaching when the fixture question has an
`explanation`. Remove the assertions:

```python
assert not any(t == "Explanation" for t in labels)
assert not any("Your answer:" in t for t in labels)
```

Replace with:

```python
assert any(t == "Correct" for t in labels)
# Teaching panel is present (objectName TeachingFeedback)
assert page.findChild(QWidget, "TeachingFeedback") is not None
```

If the fixture bank question has no explanation, set `q.explanation = "Why this is right."`
on the in-memory object before `_on_practice_question`.

- [ ] **Step 2: Run** `python -m pytest tests/gui/test_exam_flow.py::test_practice_question_check_shows_feedback -v`
  Expected: FAIL (no TeachingFeedback widget).

- [ ] **Step 3: Implement widget**

```python
"""Teaching panel: explanation + per-choice rationales (practice / review only)."""

from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout, QWidget

from openboson.bank_schema import Question


class TeachingFeedback(QFrame):
    def __init__(self, question: Question, *, is_correct: bool, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TeachingFeedback")
        v = QVBoxLayout(self)
        title = QLabel("Explanation")
        title.setProperty("role", "h2")
        v.addWidget(title)
        body = QTextBrowser()
        body.setObjectName("ExplanationBody")
        body.setOpenExternalLinks(False)
        text = (question.explanation or "").strip() or "No explanation written for this item yet."
        body.setMarkdown(text)
        v.addWidget(body)
        if question.choices:
            for ch in question.choices:
                if not (ch.rationale or "").strip():
                    continue
                line = QLabel(f"{ch.id}. {ch.rationale.strip()}")
                line.setWordWrap(True)
                line.setProperty("role", "muted")
                v.addWidget(line)
```

Wire into `PracticeQuestionPage._render_feedback` after the Correct/Incorrect
banner. Do not show this widget from `ExamSessionPage`.

- [ ] **Step 4: Re-run the test — PASS.** Also keep
  `test_practice_question_next_advances_queue` green.

- [ ] **Step 5: Commit** `feat(exsim): show explanations after practice Check`

---

### Task 2: Exam review cards

**Files:**
- Modify: `src/openboson/gui/pages/exam_review_page.py`
- Modify: `tests/gui/test_exam_flow.py` (review assertions)

- [ ] After `Your answer:` on each review card, add `TeachingFeedback(q, is_correct=...)`.
- [ ] Timed exam session: grep `ExamSessionPage` — zero references to
  `TeachingFeedback` or `explanation`.
- [ ] Commit `feat(exsim): show explanations on exam review`

---

### Task 3: Policy docs

**Files:**
- `docs/content-authoring.md` (explanations are used by practice + review)
- Do not restore explanations on score HTML/CSV redacted export.

Boson gate: a candidate can learn why they were wrong without leaving the app.
Exam pressure remains Boson-sim-like (silent).
