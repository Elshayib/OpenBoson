"""OpenBoson main window — sidebar navigation + stacked content pages."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from openboson import __version__
from openboson.gui.pages import (
    DashboardPage,
    ExamsPage,
    LabsPage,
    SettingsPage,
    StatsPage,
)


class MainWindow(QMainWindow):
    """Primary application window with a sidebar and stacked content area."""

    PAGES: list[tuple[str, type]] = [
        ("Dashboard", DashboardPage),
        ("Exams", ExamsPage),
        ("Labs", LabsPage),
        ("Stats", StatsPage),
        ("Settings", SettingsPage),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OpenBoson")
        self.resize(1280, 800)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        brand = QPushButton("OpenBoson")
        brand.setObjectName("Brand")
        brand.setEnabled(False)
        brand.setFixedHeight(56)
        side_layout.addWidget(brand)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for label, _cls in self.PAGES:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            side_layout.addWidget(btn)
            self._nav_group.addButton(btn)
        side_layout.addStretch()

        # Page stack
        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}
        for label, cls in self.PAGES:
            page = cls()
            self._pages[label] = page
            self._stack.addWidget(page)

        # Wire nav: clicking a sidebar button flips the stack page.
        self._nav_group.buttonClicked.connect(self._on_nav_clicked)

        # Select the first nav button by default.
        first_btn = self._nav_group.buttons()[0]
        first_btn.setChecked(True)
        self._stack.setCurrentIndex(0)
        # Trigger a refresh so the initial page rebuilds content.
        self._pages[self.PAGES[0][0]].refresh()

        root.addWidget(sidebar)
        root.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        StatusBar = self.statusBar()
        StatusBar.showMessage(f"openboson {__version__}  •  CCNA 200-301 v1.1")

        # Apply the OpenBoson dark theme QSS.
        self.apply_theme()

    # -----/ Styling /-----
    def apply_theme(self) -> None:
        from pathlib import Path

        qss_path = Path(__file__).resolve().parent / "styles.qss"
        if qss_path.is_file():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # -----/ Navigation /-----
    def _on_nav_clicked(self, button: QPushButton) -> None:
        label = button.text()
        idx = next((i for i, (lbl, _c) in enumerate(self.PAGES) if lbl == label), None)
        if idx is not None:
            self._stack.setCurrentIndex(idx)
            page = self._pages.get(label)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()

    # -----/ Test hooks /-----
    def visible_page_label(self) -> str:
        """Return the title of the currently visible page (test helper)."""
        widget = self._stack.currentWidget()
        return getattr(widget, "title", widget.__class__.__name__)

    def select_page(self, label: str) -> None:
        """Programmatically activate a sidebar page (test helper)."""
        for btn in self._nav_group.buttons():
            if btn.text() == label:
                btn.setChecked(True)
                self._on_nav_clicked(btn)
                return
        raise KeyError(f"No page named {label!r}")
