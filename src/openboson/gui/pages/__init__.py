"""Base placeholder pages for OpenBoson's main window.

Only Dashboard remains as a simple placeholder. Exams, Labs, Stats, and
Settings each live in their own module.
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
            "Local practice questions and blueprint exams for CCNA / CCNP,\n"
            "plus NetSim guided labs. Open Practice to browse the library or start an exam."
        )
        sub.setProperty("role", "muted")
        sub.setWordWrap(True)

        self._layout.addWidget(header)
        self._layout.addWidget(sub)
        self._layout.addStretch()
