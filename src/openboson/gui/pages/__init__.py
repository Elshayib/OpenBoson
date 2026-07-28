"""Base placeholder pages for OpenBoson's main window.

Dashboard / Stats / Settings are static pages. Exams and Labs lists live in
their own modules (``exam_list_page`` / ``lab_list_page``)."""

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
