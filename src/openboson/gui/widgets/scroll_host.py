"""Reusable scrollable content host for list/result pages.

Pages that rebuild tall content into a plain ``QVBoxLayout`` clip when the
window shrinks. Wrap that content in ``ScrollHost`` so it scrolls instead.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ScrollHost(QScrollArea):
    """Frame-less scroll area with an inner content layout.

    Typical use::

        host = ScrollHost(margins=(24, 24, 24, 24), spacing=16)
        root.addWidget(host, 1)
        host.content_layout.addWidget(header)
        # …rebuild into host.content_layout…
        host.clear_content()
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        margins: tuple[int, int, int, int] = (24, 24, 24, 24),
        spacing: int = 16,
    ) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._content = QWidget()
        self._content.setObjectName("ScrollContent")
        self._content.setAutoFillBackground(True)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(*margins)
        self._content_layout.setSpacing(spacing)
        self.setWidget(self._content)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    @property
    def content_widget(self) -> QWidget:
        return self._content

    def clear_content(self) -> None:
        """Delete all widgets and nested layouts from the content area."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_nested(item.layout())

    @staticmethod
    def _clear_nested(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                ScrollHost._clear_nested(item.layout())
