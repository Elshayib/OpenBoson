"""OpenBoson main window — sidebar navigation + stacked content pages.

The window hosts the static pages (Dashboard, Practice, Labs, Stats, Settings)
and transient exam/practice pages that are pushed onto the stack when the user
starts studying or taking an exam.
"""

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
from openboson.bank_schema import Question
from openboson.exsim.scoring import ExamResult
from openboson.exsim.session import ExamSession
from openboson.gui.pages import (
    DashboardPage,
)
from openboson.gui.pages.practice_page import PracticePage
from openboson.gui.pages.practice_question_page import PracticeQuestionPage
from openboson.gui.pages.exam_result_page import ExamResultPage
from openboson.gui.pages.exam_review_page import ExamReviewPage
from openboson.gui.pages.exam_session_page import ExamSessionPage
from openboson.gui.pages.lab_list_page import LabListPage
from openboson.gui.pages.lab_result_page import LabResultPage
from openboson.gui.pages.lab_session_page import LabSessionPage
from openboson.gui.pages.stats_page import StatsPage
from openboson.gui.pages.settings_page import SettingsPage
from openboson.netsim.session import LabResult, LabSession


class MainWindow(QMainWindow):
    """Primary application window with a sidebar and stacked content area."""

    STATIC_PAGES: list[tuple[str, type]] = [
        ("Dashboard", DashboardPage),
        ("Practice", PracticePage),
        ("Labs", LabListPage),
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
        for label, _cls in self.STATIC_PAGES:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            side_layout.addWidget(btn)
            self._nav_group.addButton(btn)
        side_layout.addStretch()

        # Page stack
        self._stack = QStackedWidget()
        self._static_pages: dict[str, QWidget] = {}
        for label, cls in self.STATIC_PAGES:
            page = cls()
            self._static_pages[label] = page
            self._stack.addWidget(page)
        self._practice_page = self._static_pages["Practice"]
        self._practice_page.set_on_practice_question(self._on_practice_question)
        self._practice_page.set_on_start_exam(self._on_blueprint_exam)

        # Transient pages
        self._practice_q_page = PracticeQuestionPage()
        self._session_page = ExamSessionPage()
        self._result_page = ExamResultPage()
        self._review_page = ExamReviewPage()
        self._stack.addWidget(self._practice_q_page)
        self._stack.addWidget(self._session_page)
        self._stack.addWidget(self._result_page)
        self._stack.addWidget(self._review_page)
        self._practice_q_page.set_on_back(self._go_to_practice)
        self._session_page.set_on_result(self._on_exam_result)
        self._session_page.set_on_exit(self._go_to_practice)
        self._result_page.set_on_review(self._on_review)
        self._result_page.set_on_retake(self._on_retake)

        self._labs_page = self._static_pages["Labs"]
        self._labs_page.set_on_lab_selected(self._on_lab_selected)

        self._settings_page = self._static_pages["Settings"]
        self._settings_page.set_on_theme_change(self._on_theme_changed)

        self._lab_session_page = LabSessionPage()
        self._lab_result_page = LabResultPage()
        self._stack.addWidget(self._lab_session_page)
        self._stack.addWidget(self._lab_result_page)
        self._lab_session_page.set_on_result(self._on_lab_result)
        self._lab_result_page.set_on_retake(self._on_lab_retake)

        self._nav_group.buttonClicked.connect(self._on_nav_clicked)

        first_btn = self._nav_group.buttons()[0]
        first_btn.setChecked(True)
        self._stack.setCurrentIndex(0)
        self._static_pages[self.STATIC_PAGES[0][0]].refresh()

        root.addWidget(sidebar)
        root.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage(f"openboson {__version__}  •  CCNA / CCNP practice")
        self.apply_theme()

    def apply_theme(self, theme: str = "dark") -> None:
        from pathlib import Path

        qss_path = Path(__file__).resolve().parent / "styles.qss"
        if qss_path.is_file():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _on_theme_changed(self, theme: str) -> None:
        self.apply_theme(theme)

    def _on_nav_clicked(self, button: QPushButton) -> None:
        label = button.text()
        idx = next(
            (i for i, (lbl, _c) in enumerate(self.STATIC_PAGES) if lbl == label),
            None,
        )
        if idx is not None:
            self._stack.setCurrentIndex(idx)
            page = self._static_pages.get(label)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()

    def _go_to_practice(self) -> None:
        idx = next(i for i, (lbl, _c) in enumerate(self.STATIC_PAGES) if lbl == "Practice")
        self._stack.setCurrentIndex(idx)
        self._practice_page.refresh()
        for btn in self._nav_group.buttons():
            if btn.text() == "Practice":
                btn.setChecked(True)

    def _on_practice_question(self, question: Question) -> None:
        self._practice_q_page.show_question(question)
        self._stack.setCurrentWidget(self._practice_q_page)

    def _on_blueprint_exam(self, session: ExamSession) -> None:
        self._session_page.start_session(session)
        self._stack.setCurrentWidget(self._session_page)

    def _on_exam_result(self, session: ExamSession, result: ExamResult) -> None:
        self._result_page.show_result(session, result)
        self._stack.setCurrentWidget(self._result_page)

    def _on_review(self, session: ExamSession) -> None:
        self._review_page.show_review(session)
        self._stack.setCurrentWidget(self._review_page)

    def _on_retake(self, session: ExamSession) -> None:
        if session.blueprint_id:
            from openboson.gui import engine

            try:
                new_session = engine.start_blueprint_exam(session.blueprint_id)
            except Exception:
                self._session_page.start_exam(session.exam, mode=session.mode)
            else:
                self._session_page.start_session(new_session)
                self._stack.setCurrentWidget(self._session_page)
                return
        self._session_page.start_exam(session.exam, mode=session.mode)
        self._stack.setCurrentWidget(self._session_page)

    def _on_lab_selected(self, lab) -> None:
        self._lab_session_page.start_lab(lab)
        self._stack.setCurrentWidget(self._lab_session_page)

    def _on_lab_result(self, session: LabSession, result: LabResult) -> None:
        self._lab_result_page.show_result(session, result)
        self._stack.setCurrentWidget(self._lab_result_page)

    def _on_lab_retake(self, session: LabSession) -> None:
        self._lab_session_page.start_lab(session.lab)
        self._stack.setCurrentWidget(self._lab_session_page)

    def visible_page_label(self) -> str:
        widget = self._stack.currentWidget()
        return getattr(widget, "title", widget.__class__.__name__)

    def select_page(self, label: str) -> None:
        for btn in self._nav_group.buttons():
            if btn.text() == label:
                btn.setChecked(True)
                self._on_nav_clicked(btn)
                return
        raise KeyError(f"No page named {label!r}")

    def start_exam_from_list(self, bank, mode) -> None:
        """Test helper: start a bank exam session."""
        self._session_page.start_exam(bank, mode=mode)
        self._stack.setCurrentWidget(self._session_page)

    def start_lab_from_list(self, lab) -> None:
        self._on_lab_selected(lab)
