"""Placeholder content pages for OpenBoson's main window.

Each page is a ``QWidget`` exposing ``title`` (used by the sidebar) and
``refresh`` (called when the user re-enters the page). Pages are empty for
the GUI shell milestone (Task 7); feature pages arrive in Task 8+.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class _Page(QWidget):
    """Base class for stacked pages."""

    title: str = "Page"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(12)

    def refresh(self) -> None:
        """Hook for reloading data when the user navigates back."""
        return None


class DashboardPage(_Page):
    title = "Dashboard"

    def __init__(self) -> None:
        super().__init__()
        header = QLabel("OpenBoson")
        header.setProperty("role", "h1")
        sub = QLabel(
            "Local ExSim practice exams and NetSim guided labs for CCNA 200-301.\n"
            "Pick an exam on the left, or open the lab browser."
        )
        sub.setProperty("role", "muted")
        sub.setWordWrap(True)

        self._layout.addWidget(header)
        self._layout.addWidget(sub)
        self._layout.addStretch()


class ExamsPage(_Page):
    title = "Exams"

    def __init__(self) -> None:
        super().__init__()
        header = QLabel("Practice Exams")
        header.setProperty("role", "h1")
        body = QLabel(
            "Exam list and exam sessions appear here in Task 8."
        )
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        self._layout.addWidget(header)
        self._layout.addWidget(body)
        self._layout.addStretch()


class LabsPage(_Page):
    title = "Labs"

    def __init__(self) -> None:
        super().__init__()
        header = QLabel("Network Labs")
        header.setProperty("role", "h1")
        body = QLabel(
            "NetSim lab browser and topology designer appear here in Phase 3."
        )
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        self._layout.addWidget(header)
        self._layout.addWidget(body)
        self._layout.addStretch()


class StatsPage(_Page):
    title = "Stats"

    def __init__(self) -> None:
        super().__init__()
        header = QLabel("Statistics")
        header.setProperty("role", "h1")
        body = QLabel("Per-domain performance and weak areas appear here in Phase 4.")
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        self._layout.addWidget(header)
        self._layout.addWidget(body)
        self._layout.addStretch()


class SettingsPage(_Page):
    title = "Settings"

    def __init__(self) -> None:
        super().__init__()
        header = QLabel("Settings")
        header.setProperty("role", "h1")
        body = QLabel(
            "Theme, default exam mode, and storage location settings appear here."
        )
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        self._layout.addWidget(header)
        self._layout.addWidget(body)
        self._layout.addStretch()
