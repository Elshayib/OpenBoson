"""Base placeholder pages for OpenBoson's main window.

Only Dashboard remains here; Practice, Labs, Stats, and Settings each live in
their own module.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from openboson.gui.widgets.scroll_host import ScrollHost


class _Page(QWidget):
    """Base class for stacked pages."""

    title: str = "Page"

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._scroll = ScrollHost(margins=(24, 24, 24, 24), spacing=12)
        root.addWidget(self._scroll, 1)
        self._layout = self._scroll.content_layout

    def refresh(self) -> None:
        """Hook for reloading data when the user navigates back."""
        return None


class DashboardPage(_Page):
    title = "Dashboard"

    def __init__(self) -> None:
        super().__init__()
        self._on_practice_weakest: Callable[[], None] | None = None
        self._on_practice_missed: Callable[[], None] | None = None
        self._on_continue: Callable[[], None] | None = None
        self._on_resume_exam: Callable[[], None] | None = None
        self._cta_host: QWidget | None = None
        self._rebuild_static()

    def set_on_practice_weakest(self, callback: Callable[[], None]) -> None:
        self._on_practice_weakest = callback

    def set_on_practice_missed(self, callback: Callable[[], None]) -> None:
        self._on_practice_missed = callback

    def set_on_continue(self, callback: Callable[[], None]) -> None:
        self._on_continue = callback

    def set_on_resume_exam(self, callback: Callable[[], None]) -> None:
        self._on_resume_exam = callback

    def _rebuild_static(self) -> None:
        self._scroll.clear_content()

        header = QLabel("OpenBoson")
        header.setProperty("role", "h1")
        sub = QLabel(
            "Local practice questions and blueprint exams for CCNA 200-301 v1.1 and "
            "CCNP ENCOR 350-401 v1.2, plus NetSim guided labs. Open Practice to browse "
            "the library or start an exam."
        )
        sub.setProperty("role", "muted")
        sub.setWordWrap(True)

        self._layout.addWidget(header)
        self._layout.addWidget(sub)

        self._cta_host = QWidget()
        self._cta_layout = QVBoxLayout(self._cta_host)
        self._cta_layout.setContentsMargins(0, 8, 0, 0)
        self._cta_layout.setSpacing(12)
        self._layout.addWidget(self._cta_host)
        self._layout.addStretch()

    def refresh(self) -> None:
        if self._cta_host is None:
            self._rebuild_static()
        while self._cta_layout.count():
            item = self._cta_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        try:
            from openboson import stats_service as svc
            from openboson.gui import engine as gui_engine

            weak = svc.weak_domains(limit=1)
            missed = svc.recent_missed_question_ids(limit=1)
            activity = svc.latest_activity()
            summary = svc.exam_summary()
            resumable = gui_engine.get_resumable_exam_info()
        except Exception as exc:
            err = QLabel(f"Could not load dashboard: {exc}")
            err.setProperty("role", "muted")
            self._cta_layout.addWidget(err)
            return

        if resumable is not None:
            rem = resumable.remaining_seconds
            rem_txt = ""
            if rem is not None:
                mins, secs = divmod(max(0, rem), 60)
                rem_txt = f" · {mins:02d}:{secs:02d} left"
            self._cta_layout.addWidget(
                self._cta_card(
                    "Resume paused exam",
                    (
                        f"{resumable.exam_title} — question {resumable.current_index + 1}/"
                        f"{max(resumable.question_count, 1)} · "
                        f"{resumable.answered_count} answered{rem_txt}"
                    ),
                    enabled=True,
                    on_click=self._on_resume_exam,
                )
            )

        self._cta_layout.addWidget(self._section("Study next"))

        row = QHBoxLayout()
        row.addWidget(
            self._cta_card(
                "Practice weakest domain",
                (
                    f"Domain {weak[0].domain_prefix.rstrip('.')} — "
                    f"{int(weak[0].percent * 100)}% accuracy"
                    if weak
                    else "Take an exam to unlock weak-domain practice"
                ),
                enabled=bool(weak),
                on_click=self._on_practice_weakest,
            )
        )
        row.addWidget(
            self._cta_card(
                "Practice missed questions",
                (
                    "Review questions you got wrong recently"
                    if missed
                    else "No missed questions yet"
                ),
                enabled=bool(missed),
                on_click=self._on_practice_missed,
            )
        )
        continue_sub = "Start a new practice session"
        if activity:
            if activity["kind"] == "exam":
                continue_sub = (
                    f"Last exam: {activity.get('exam_code', 'unknown')} "
                    f"({int((activity.get('score') or 0) * 100)}%) — open Practice"
                )
            else:
                continue_sub = f"Last lab: {activity.get('lab_id', 'unknown')} — open Labs"
        elif summary.get("total_exams", 0) == 0:
            continue_sub = "No history yet — open Practice to begin"
        row.addWidget(
            self._cta_card(
                "Continue latest activity",
                continue_sub,
                enabled=True,
                on_click=self._on_continue,
            )
        )
        host = QWidget()
        host.setLayout(row)
        self._cta_layout.addWidget(host)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("role", "h2")
        return lbl

    def _cta_card(
        self,
        title: str,
        subtitle: str,
        *,
        enabled: bool,
        on_click: Callable[[], None] | None,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        t = QLabel(title)
        t.setProperty("role", "h2")
        t.setWordWrap(True)
        v.addWidget(t)
        s = QLabel(subtitle)
        s.setProperty("role", "muted")
        s.setWordWrap(True)
        v.addWidget(s)
        btn = QPushButton("Go")
        btn.setObjectName("Primary" if enabled else "Secondary")
        btn.setEnabled(enabled and on_click is not None)
        if on_click is not None:
            btn.clicked.connect(on_click)
        v.addWidget(btn)
        return card
