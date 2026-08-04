"""OpenBoson main window — sidebar navigation + stacked content pages.

The window hosts the static pages (Dashboard, Practice, Labs, Stats, Settings)
and transient exam/practice pages that are pushed onto the stack when the user
starts studying or taking an exam.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
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
from openboson.gui.pages.custom_exam_page import CustomExamPage
from openboson.gui.pages.exam_result_page import ExamResultPage
from openboson.gui.pages.exam_review_page import ExamReviewPage
from openboson.gui.pages.exam_session_page import ExamSessionPage
from openboson.gui.pages.lab_list_page import LabListPage
from openboson.gui.pages.lab_result_page import LabResultPage
from openboson.gui.pages.lab_session_page import LabSessionPage
from openboson.gui.pages.practice_page import PracticePage
from openboson.gui.pages.practice_question_page import PracticeQuestionPage
from openboson.gui.pages.settings_page import SettingsPage
from openboson.gui.pages.stats_page import StatsPage
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
        self.setMinimumSize(960, 640)

        central = QWidget()
        central.setObjectName("Content")
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
        side_layout.addSpacing(8)

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
        self._practice_page.set_on_custom_exam(self._open_custom_exam)

        self._dashboard_page = self._static_pages["Dashboard"]
        self._dashboard_page.set_on_practice_weakest(self.navigate_practice_weakest_domain)
        self._dashboard_page.set_on_practice_missed(self.navigate_practice_missed)
        self._dashboard_page.set_on_continue(self.navigate_continue_activity)
        self._dashboard_page.set_on_resume_exam(self.resume_paused_exam)

        # Transient pages
        self._practice_q_page = PracticeQuestionPage()
        self._custom_exam_page = CustomExamPage()
        self._session_page = ExamSessionPage()
        self._result_page = ExamResultPage()
        self._review_page = ExamReviewPage()
        self._stack.addWidget(self._practice_q_page)
        self._stack.addWidget(self._custom_exam_page)
        self._stack.addWidget(self._session_page)
        self._stack.addWidget(self._result_page)
        self._stack.addWidget(self._review_page)
        self._practice_q_page.set_on_back(self._go_to_practice)
        self._custom_exam_page.set_on_back(self._go_to_practice)
        self._custom_exam_page.set_on_start(self._on_blueprint_exam)
        self._session_page.set_on_result(self._on_exam_result)
        self._session_page.set_on_exit(self._go_to_practice)
        self._session_page.set_on_paused(self._on_exam_paused)
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

        self.statusBar().showMessage(
            f"openboson {__version__}  •  CCNA 200-301 v1.1 / ENCOR 350-401 v1.2"
        )
        try:
            from openboson.settings_store import load_settings

            self.apply_theme(load_settings().theme)
        except Exception:
            self.apply_theme("dark")
        self._exam_active = False
        self._nav_before_exam: QPushButton | None = None
        self._update_thread = None
        self._update_worker = None
        self._startup_update_pending = None
        # Defer startup update check until the window is shown and interactive.
        QTimer.singleShot(750, self._maybe_startup_update_check)

    def apply_theme(self, theme: str = "dark") -> None:
        from pathlib import Path

        from PySide6.QtGui import QColor, QPalette
        from PySide6.QtWidgets import QApplication

        name = "styles_light.qss" if theme == "light" else "styles.qss"
        qss_path = Path(__file__).resolve().parent / name
        if qss_path.is_file():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        else:
            # Fall back to dark stylesheet if light asset is missing.
            dark = Path(__file__).resolve().parent / "styles.qss"
            if dark.is_file():
                self.setStyleSheet(dark.read_text(encoding="utf-8"))

        # Scroll-area viewports and unstyled surfaces follow the app palette
        # (Base / Window), not only QSS — keep them in sync with the theme.
        app = QApplication.instance()
        if app is not None:
            pal = QPalette()
            if theme == "light":
                window = QColor("#f5f7fb")
                base = QColor("#ffffff")
                text = QColor("#1f2328")
                muted = QColor("#656d76")
                highlight = QColor("#0969da")
                button = QColor("#ffffff")
            else:
                window = QColor("#0f1420")
                base = QColor("#0b1019")
                text = QColor("#e6edf3")
                muted = QColor("#8b949e")
                highlight = QColor("#2f81f7")
                button = QColor("#161b27")
            pal.setColor(QPalette.ColorRole.Window, window)
            pal.setColor(QPalette.ColorRole.WindowText, text)
            pal.setColor(QPalette.ColorRole.Base, base)
            pal.setColor(QPalette.ColorRole.AlternateBase, window)
            pal.setColor(QPalette.ColorRole.Text, text)
            pal.setColor(QPalette.ColorRole.Button, button)
            pal.setColor(QPalette.ColorRole.ButtonText, text)
            pal.setColor(QPalette.ColorRole.ToolTipBase, base)
            pal.setColor(QPalette.ColorRole.ToolTipText, text)
            pal.setColor(QPalette.ColorRole.PlaceholderText, muted)
            pal.setColor(QPalette.ColorRole.Highlight, highlight)
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            app.setPalette(pal)

        # Re-polish widgets that rely on dynamic QSS properties (e.g. MatchSlot).
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def _on_theme_changed(self, theme: str) -> None:
        self.apply_theme(theme)

    def _on_nav_clicked(self, button: QPushButton) -> None:
        if self._exam_active:
            # Keep the user on the exam; restore the previously checked nav button.
            if self._nav_before_exam is not None:
                self._nav_before_exam.setChecked(True)
            else:
                button.setChecked(False)
            self.statusBar().showMessage(
                "Finish, pause, or wait for the timer before leaving.", 4000
            )
            return
        label = button.text()
        idx = next(
            (i for i, (lbl, _c) in enumerate(self.STATIC_PAGES) if lbl == label),
            None,
        )
        if idx is not None:
            # Switch first so the tab feels instant; refresh after the paint.
            self._stack.setCurrentIndex(idx)
            page = self._static_pages.get(label)
            if page is not None and hasattr(page, "refresh"):
                QTimer.singleShot(0, page.refresh)

    def _enter_exam(self) -> None:
        self._exam_active = True
        checked = self._nav_group.checkedButton()
        self._nav_before_exam = checked
        for btn in self._nav_group.buttons():
            btn.setChecked(False)
        self._stack.setCurrentWidget(self._session_page)

    def _leave_exam(self) -> None:
        self._exam_active = False
        self._session_page.cleanup()
        self._nav_before_exam = None

    def _go_to_practice(self) -> None:
        self._leave_exam()
        idx = next(i for i, (lbl, _c) in enumerate(self.STATIC_PAGES) if lbl == "Practice")
        self._stack.setCurrentIndex(idx)
        self._practice_page.refresh(refresh_list=True)
        for btn in self._nav_group.buttons():
            if btn.text() == "Practice":
                btn.setChecked(True)

    def navigate_practice(
        self,
        *,
        cert: str | None = None,
        topic_code: str | None = None,
        question_ids: list[str] | None = None,
    ) -> None:
        """Navigate to Practice with an optional deep-link filter."""
        self._leave_exam()
        idx = next(i for i, (lbl, _c) in enumerate(self.STATIC_PAGES) if lbl == "Practice")
        self._stack.setCurrentIndex(idx)
        for btn in self._nav_group.buttons():
            if btn.text() == "Practice":
                btn.setChecked(True)
        if cert or topic_code or question_ids is not None:
            self._practice_page.apply_deep_link(
                cert=cert, topic_code=topic_code, question_ids=question_ids
            )
        else:
            self._practice_page.refresh()

    def navigate_practice_weakest_domain(self, cert: str | None = None) -> None:
        from openboson import stats_service as svc

        weak = svc.weak_domains(cert=cert, limit=1)
        if not weak:
            self.navigate_practice()
            return
        domain = weak[0]
        self.navigate_practice(cert=domain.cert_tag or cert, topic_code=domain.domain_prefix)

    def navigate_practice_missed(self, limit: int = 20) -> None:
        from openboson import stats_service as svc

        ids = svc.recent_missed_question_ids(limit=limit)
        self.navigate_practice(question_ids=ids)

    def _on_exam_paused(self, session: ExamSession) -> None:
        """Leave the exam UI after Pause & Exit; attempt is saved as paused."""
        self._exam_active = False
        self._session_page.cleanup()
        self._nav_before_exam = None
        self.select_page("Dashboard")
        remaining = session.remaining_seconds
        msg = "Exam paused — resume from the Dashboard."
        if remaining is not None:
            mins, secs = divmod(max(0, remaining), 60)
            msg = f"Exam paused with {mins:02d}:{secs:02d} remaining — resume from the Dashboard."
        self.statusBar().showMessage(msg, 8000)

    def navigate_continue_activity(self) -> None:
        """Prefer resumable exam; else open Practice or Labs from last finished activity."""
        if self.resume_paused_exam():
            return
        from openboson import stats_service as svc

        activity = svc.latest_activity()
        if activity and activity.get("kind") == "lab":
            self.select_page("Labs")
            return
        self.navigate_practice()

    def resume_paused_exam(self) -> bool:
        """Load and show a resumable exam. Returns True if one was resumed."""
        from openboson.gui import engine as gui_engine

        info = gui_engine.get_resumable_exam_info()
        if info is None:
            return False
        extra = None
        local = getattr(self._session_page, "_session", None)
        if local is not None and local.session_id == info.engine_session_id:
            extra = {q.id: q for q in local.questions}
        session = gui_engine.load_resumable_exam(info.engine_session_id, extra_questions=extra)
        if session is None:
            self.statusBar().showMessage(
                "Could not restore the saved exam — questions may be missing from the pool.",
                8000,
            )
            return False
        if session.is_paused():
            gui_engine.resume_session(session)
        self._session_page.start_session(session, start_timer=True)
        self._enter_exam()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt override
        """Flush in-progress exam progress so remaining time survives quit."""
        if self._session_page.is_exam_active():
            self._session_page.flush_progress()
        super().closeEvent(event)

    def _confirm_replace_active_exam(self) -> bool:
        """Ask before abandoning a paused/in-progress exam to start a new one."""
        from openboson.gui import engine as gui_engine

        info = gui_engine.get_resumable_exam_info()
        if info is None:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Exam in progress")
        box.setText(f"You have a saved exam: {info.exam_title}.")
        box.setInformativeText("Resume the saved exam, or abandon it and start a new one?")
        resume_btn = box.addButton("Resume saved", QMessageBox.ButtonRole.AcceptRole)
        abandon_btn = box.addButton("Abandon & start new", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(resume_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is resume_btn:
            self.resume_paused_exam()
            return False
        if clicked is abandon_btn:
            gui_engine.abandon_resumable_exams()
            return True
        return False

    def _on_practice_question(
        self,
        question: Question,
        *,
        queue: list[Question] | None = None,
    ) -> None:
        self._practice_q_page.show_question(question, queue=queue)
        self._stack.setCurrentWidget(self._practice_q_page)

    def _open_custom_exam(self) -> None:
        self._custom_exam_page.refresh()
        self._stack.setCurrentWidget(self._custom_exam_page)

    def _on_blueprint_exam(self, session: ExamSession) -> None:
        if not self._confirm_replace_active_exam():
            return
        self._session_page.start_session(session)
        self._enter_exam()

    def _on_exam_result(self, session: ExamSession, result: ExamResult) -> None:
        from openboson.gui import engine as gui_engine

        self._leave_exam()
        self._result_page.show_result(session, result)
        self._stack.setCurrentWidget(self._result_page)
        if gui_engine.last_persistence_warning:
            self.statusBar().showMessage(gui_engine.last_persistence_warning, 8000)

    def _on_review(self, session: ExamSession) -> None:
        self._review_page.show_review(session)
        self._stack.setCurrentWidget(self._review_page)

    def _on_retake(self, session: ExamSession) -> None:
        """Start a fresh attempt; blueprint/custom fallback runs start exactly once."""
        from openboson.gui import engine

        if session.custom_preset_id:
            try:
                new_session = engine.start_custom_exam(session.custom_preset_id)
            except Exception:
                self._session_page.start_exam(session.exam, mode=session.mode)
            else:
                self._session_page.start_session(new_session)
                self._enter_exam()
                return
            self._enter_exam()
            return
        if session.blueprint_id:
            try:
                new_session = engine.start_blueprint_exam(session.blueprint_id)
            except Exception:
                self._session_page.start_exam(session.exam, mode=session.mode)
            else:
                self._session_page.start_session(new_session)
                self._enter_exam()
                return
            self._enter_exam()
            return
        self._session_page.start_exam(session.exam, mode=session.mode)
        self._enter_exam()

    def _on_lab_selected(self, lab) -> None:
        self._lab_session_page.start_lab(lab)
        self._stack.setCurrentWidget(self._lab_session_page)

    def _on_lab_result(self, session: LabSession, result: LabResult) -> None:
        self._lab_session_page.cleanup()
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
        if not self._confirm_replace_active_exam():
            return
        self._session_page.start_exam(bank, mode=mode)
        self._enter_exam()

    def start_lab_from_list(self, lab) -> None:
        self._on_lab_selected(lab)

    def has_active_study_session(self) -> bool:
        """True while an exam or lab session should not be interrupted by update UI."""
        if self._exam_active:
            return True
        if self._stack.currentWidget() is self._lab_session_page:
            return bool(getattr(self._lab_session_page, "is_lab_active", lambda: False)())
        return False

    def _maybe_startup_update_check(self) -> None:
        from openboson.updater import should_run_startup_check

        if not should_run_startup_check():
            return
        if self.has_active_study_session():
            # Retry shortly — exam/lab may end; avoid blocking or interrupting.
            QTimer.singleShot(5000, self._maybe_startup_update_check)
            return
        self._start_background_update_check(force=False)

    def _start_background_update_check(self, *, force: bool) -> None:
        from openboson.gui.update_check import start_check_thread

        def _on_finished(result: object) -> None:
            self._on_startup_update_result(result)

        self._update_thread, self._update_worker = start_check_thread(
            force=force,
            on_finished=_on_finished,
        )

    def _on_startup_update_result(self, result: object) -> None:
        from openboson.updater import CheckResult, CheckStatus

        if not isinstance(result, CheckResult):
            return
        if result.status != CheckStatus.UPDATE_AVAILABLE or result.update is None:
            if result.status == CheckStatus.ERROR:
                self.statusBar().showMessage(result.message, 6000)
            return
        if self.has_active_study_session():
            # Defer notification until the session ends.
            self._startup_update_pending = result.update
            QTimer.singleShot(5000, self._flush_pending_update_banner)
            return
        self._show_update_available(result.update)

    def _flush_pending_update_banner(self) -> None:
        pending = self._startup_update_pending
        if pending is None:
            return
        if self.has_active_study_session():
            QTimer.singleShot(5000, self._flush_pending_update_banner)
            return
        self._startup_update_pending = None
        self._show_update_available(pending)

    def _show_update_available(self, update) -> None:
        from openboson.updater import skip_version

        self.statusBar().showMessage(f"Update {update.version} is available.", 10000)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Update available")
        box.setText(f"OpenBoson {update.version} is available.")
        box.setInformativeText(
            "You can download and install from Settings → Updates. "
            "Windows installers are currently unsigned; SmartScreen may warn before install.\n\n"
            f"Release notes: {update.release_url}"
        )
        install_btn = box.addButton("Open Settings", QMessageBox.ButtonRole.AcceptRole)
        later_btn = box.addButton("Remind later", QMessageBox.ButtonRole.RejectRole)
        skip_btn = box.addButton("Skip this version", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(later_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is install_btn:
            self.select_page("Settings")
        elif clicked is skip_btn:
            skip_version(update.version)
        # Remind later: dismiss only.
