"""Settings page — two-column prefs (section nav + detail)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import asdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from openboson.config import settings
from openboson.gui.update_check import start_check_thread, start_download_thread
from openboson.gui.widgets.scroll_host import ScrollHost
from openboson.logging_setup import logs_dir
from openboson.settings_store import load_settings, save_settings, update_settings
from openboson.updater import (
    CheckResult,
    CheckStatus,
    DownloadResult,
    UpdateInfo,
    launch_installer,
    skip_version,
    updates_enabled,
)


def _open_path(path: str) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["explorer", path])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class SettingsPage(QWidget):
    title = "Settings"

    SECTIONS = ("Appearance", "Content", "Updates", "Advanced")

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._scroll = ScrollHost(margins=(12, 12, 12, 12), spacing=8)
        root.addWidget(self._scroll, 1)
        self._layout = self._scroll.content_layout
        self._on_theme_change = None
        self._pending_update: UpdateInfo | None = None
        self._check_thread = None
        self._check_worker = None
        self._download_thread = None
        self._download_worker = None
        self._update_status: QLabel | None = None
        self._download_btn: QPushButton | None = None
        self._remind_btn: QPushButton | None = None
        self._skip_btn: QPushButton | None = None
        self._check_now_btn: QPushButton | None = None
        self._section_stack: QStackedWidget | None = None
        self._nav_group: QButtonGroup | None = None
        self._built = False

    def set_on_theme_change(self, cb) -> None:
        self._on_theme_change = cb

    def refresh(self) -> None:
        if not self._built:
            self._rebuild()
            self._built = True

    def _rebuild(self) -> None:
        self._scroll.clear_content()

        header = QLabel("Settings")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        cfg = load_settings()

        body = QHBoxLayout()
        body.setSpacing(8)

        # Left section nav
        nav = QFrame()
        nav.setObjectName("SettingsNav")
        nav.setFixedWidth(140)
        nl = QVBoxLayout(nav)
        nl.setContentsMargins(6, 8, 6, 8)
        nl.setSpacing(2)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for i, name in enumerate(self.SECTIONS):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            self._nav_group.addButton(btn, i)
            nl.addWidget(btn)
        nl.addStretch()
        self._nav_group.idClicked.connect(self._on_section_changed)
        body.addWidget(nav)

        # Right detail stack
        self._section_stack = QStackedWidget()
        self._section_stack.addWidget(self._build_appearance(cfg))
        self._section_stack.addWidget(self._build_content())
        self._section_stack.addWidget(self._build_updates(cfg))
        self._section_stack.addWidget(self._build_advanced())
        body.addWidget(self._section_stack, 1)

        host = QWidget()
        host.setLayout(body)
        self._layout.addWidget(host, 1)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        self._layout.addWidget(save_btn)

    def _on_section_changed(self, index: int) -> None:
        if self._section_stack is not None:
            self._section_stack.setCurrentIndex(index)

    def _build_appearance(self, cfg) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        theme_card = QFrame()
        theme_card.setObjectName("Card")
        tl = QVBoxLayout(theme_card)
        tl.setContentsMargins(12, 10, 12, 10)
        tl.setSpacing(6)
        tl.addWidget(self._label("Theme", "h2"))
        hint = QLabel("Soft Daylight is the default study theme.")
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        tl.addWidget(hint)
        self._theme_group = QButtonGroup(self)
        self._dark_btn = QRadioButton("Dark")
        self._light_btn = QRadioButton("Soft Daylight")
        self._theme_group.addButton(self._dark_btn)
        self._theme_group.addButton(self._light_btn)
        if cfg.theme == "light":
            self._light_btn.setChecked(True)
        else:
            self._dark_btn.setChecked(True)
        row = QHBoxLayout()
        row.addWidget(self._dark_btn)
        row.addWidget(self._light_btn)
        row.addStretch()
        tl.addLayout(row)
        layout.addWidget(theme_card)
        layout.addStretch()
        return wrap

    def _build_content(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        content_card = QFrame()
        content_card.setObjectName("Card")
        cl = QVBoxLayout(content_card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(6)
        cl.addWidget(self._label("Content", "h2"))

        from openboson.gui import engine as gui_engine

        diag = gui_engine.content_diagnostics()
        summary = QLabel(f"Accepted: {diag.accepted_count}  ·  Rejected: {diag.rejected_count}")
        summary.setProperty("role", "muted")
        summary.setWordWrap(True)
        cl.addWidget(summary)

        if diag.rejected:
            reasons = []
            for item in diag.rejected[:5]:
                reasons.append(f"• {item.provenance}: {item.reason}")
            if diag.rejected_count > 5:
                reasons.append(f"• …and {diag.rejected_count - 5} more")
            detail = QLabel("\n".join(reasons))
            detail.setProperty("role", "muted")
            detail.setWordWrap(True)
            cl.addWidget(detail)

        refresh_btn = QPushButton("Refresh content")
        refresh_btn.setObjectName("Secondary")
        refresh_btn.clicked.connect(self._refresh_content)
        cl.addWidget(refresh_btn)
        layout.addWidget(content_card)
        layout.addStretch()
        return wrap

    def _build_updates(self, cfg) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        updates_card = QFrame()
        updates_card.setObjectName("Card")
        ul = QVBoxLayout(updates_card)
        ul.setContentsMargins(12, 10, 12, 10)
        ul.setSpacing(6)
        ul.addWidget(self._label("Updates", "h2"))

        if not updates_enabled():
            disabled = QLabel(
                "Automatic update checks are disabled "
                "(set OPENBOSON_SKIP_UPDATE=1, or no repository identity)."
            )
            disabled.setWordWrap(True)
            disabled.setProperty("role", "muted")
            ul.addWidget(disabled)
        else:
            channel_lbl = QLabel("Release channel")
            channel_lbl.setProperty("role", "muted")
            ul.addWidget(channel_lbl)
            self._channel_group = QButtonGroup(self)
            self._stable_btn = QRadioButton("Stable")
            self._beta_btn = QRadioButton("Beta (includes -beta.N prereleases)")
            self._channel_group.addButton(self._stable_btn)
            self._channel_group.addButton(self._beta_btn)
            if cfg.update_channel == "beta":
                self._beta_btn.setChecked(True)
            else:
                self._stable_btn.setChecked(True)
            ch_row = QHBoxLayout()
            ch_row.addWidget(self._stable_btn)
            ch_row.addWidget(self._beta_btn)
            ch_row.addStretch()
            ul.addLayout(ch_row)

            self._startup_check = QCheckBox("Check for updates on startup")
            self._startup_check.setChecked(cfg.check_updates_on_startup)
            ul.addWidget(self._startup_check)

            note = QLabel(
                "Windows installers are currently unsigned. Windows SmartScreen may warn "
                "before install; confirm the publisher details in SUPPORT.md before continuing."
            )
            note.setWordWrap(True)
            note.setProperty("role", "muted")
            ul.addWidget(note)

            action_row = QHBoxLayout()
            self._check_now_btn = QPushButton("Check now")
            self._check_now_btn.setObjectName("Secondary")
            self._check_now_btn.clicked.connect(self._check_now)
            action_row.addWidget(self._check_now_btn)
            action_row.addStretch()
            ul.addLayout(action_row)

            self._update_status = QLabel("No update check run yet.")
            self._update_status.setWordWrap(True)
            self._update_status.setProperty("role", "muted")
            ul.addWidget(self._update_status)

            update_actions = QHBoxLayout()
            self._download_btn = QPushButton("Download and install")
            self._download_btn.setObjectName("Primary")
            self._download_btn.setEnabled(False)
            self._download_btn.clicked.connect(self._download_and_install)
            update_actions.addWidget(self._download_btn)

            self._remind_btn = QPushButton("Remind later")
            self._remind_btn.setObjectName("Secondary")
            self._remind_btn.setEnabled(False)
            self._remind_btn.clicked.connect(self._remind_later)
            update_actions.addWidget(self._remind_btn)

            self._skip_btn = QPushButton("Skip this version")
            self._skip_btn.setObjectName("Secondary")
            self._skip_btn.setEnabled(False)
            self._skip_btn.clicked.connect(self._skip_this_version)
            update_actions.addWidget(self._skip_btn)
            update_actions.addStretch()
            ul.addLayout(update_actions)

        layout.addWidget(updates_card)
        layout.addStretch()
        return wrap

    def _build_advanced(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        dir_card = QFrame()
        dir_card.setObjectName("Card")
        dl = QVBoxLayout(dir_card)
        dl.setContentsMargins(12, 10, 12, 10)
        dl.setSpacing(6)
        dl.addWidget(self._label("Data Directory", "h2"))
        path_lbl = QLabel(str(settings.data_dir))
        path_lbl.setProperty("role", "muted")
        path_lbl.setWordWrap(True)
        dl.addWidget(path_lbl)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open data folder")
        open_btn.setObjectName("Secondary")
        open_btn.clicked.connect(lambda: _open_path(str(settings.data_dir)))
        btn_row.addWidget(open_btn)

        logs_btn = QPushButton("Open logs")
        logs_btn.setObjectName("Secondary")
        logs_btn.clicked.connect(lambda: _open_path(str(logs_dir())))
        btn_row.addWidget(logs_btn)

        backups_btn = QPushButton("Open backups")
        backups_btn.setObjectName("Secondary")

        def _open_backups() -> None:
            from openboson.db_backup import backups_dir

            _open_path(str(backups_dir()))

        backups_btn.clicked.connect(_open_backups)
        btn_row.addWidget(backups_btn)
        btn_row.addStretch()
        dl.addLayout(btn_row)

        reset_btn = QPushButton("Reset cache")
        reset_btn.setObjectName("Secondary")
        reset_btn.clicked.connect(self._reset_cache)
        dl.addWidget(reset_btn)
        layout.addWidget(dir_card)
        layout.addStretch()
        return wrap

    def _label(self, text: str, role: str = "muted") -> QLabel:
        label = QLabel(text)
        label.setProperty("role", role)
        return label

    def _refresh_content(self) -> None:
        from openboson.gui import engine as gui_engine

        diag = gui_engine.refresh_content()
        QMessageBox.information(
            self,
            "Content refreshed",
            f"Accepted {diag.accepted_count} file(s), rejected {diag.rejected_count}.",
        )
        # Force a full rebuild so content diagnostics stay accurate.
        self._built = False
        self._rebuild()
        self._built = True

    def _reset_cache(self) -> None:
        cache = settings.data_dir / "cache"
        if cache.exists():
            import shutil

            shutil.rmtree(cache, ignore_errors=True)
        QMessageBox.information(self, "Cache reset", "Local cache cleared.")

    def _save(self) -> None:
        theme = "light" if self._light_btn.isChecked() else "dark"
        kwargs: dict = {"theme": theme}
        if updates_enabled() and hasattr(self, "_stable_btn"):
            kwargs["update_channel"] = "beta" if self._beta_btn.isChecked() else "stable"
            kwargs["check_updates_on_startup"] = self._startup_check.isChecked()
        update_settings(**kwargs)
        if self._on_theme_change:
            self._on_theme_change(theme)

    def _set_status(self, text: str) -> None:
        if self._update_status is not None:
            self._update_status.setText(text)

    def _set_update_actions(self, enabled: bool) -> None:
        for btn in (self._download_btn, self._remind_btn, self._skip_btn):
            if btn is not None:
                btn.setEnabled(enabled)

    def _check_now(self) -> None:
        if not updates_enabled():
            return
        # Persist channel/startup prefs before checking.
        self._save()
        if self._check_now_btn is not None:
            self._check_now_btn.setEnabled(False)
        self._set_status("Checking for updates…")
        self._set_update_actions(False)
        self._pending_update = None

        def _on_finished(result: object) -> None:
            self._on_check_finished(result)  # type: ignore[arg-type]

        self._check_thread, self._check_worker = start_check_thread(
            force=True,
            on_finished=_on_finished,
        )

    def _on_check_finished(self, result: CheckResult) -> None:
        if self._check_now_btn is not None:
            self._check_now_btn.setEnabled(True)
        if result.status == CheckStatus.UPDATE_AVAILABLE and result.update is not None:
            self._pending_update = result.update
            self._set_status(
                f"Update {result.update.version} is available. "
                f"Release notes: {result.update.release_url}"
            )
            self._set_update_actions(True)
        elif result.status == CheckStatus.SKIPPED and result.update is not None:
            self._pending_update = result.update
            self._set_status(result.message)
            self._set_update_actions(True)
        elif result.status == CheckStatus.UP_TO_DATE:
            self._pending_update = None
            self._set_status(result.message)
            self._set_update_actions(False)
        else:
            self._pending_update = None
            self._set_status(result.message)
            self._set_update_actions(False)

    def _remind_later(self) -> None:
        self._pending_update = None
        self._set_update_actions(False)
        self._set_status("Reminder dismissed. You can check again later.")

    def _skip_this_version(self) -> None:
        if self._pending_update is None:
            return
        skip_version(self._pending_update.version)
        self._set_status(f"Skipped version {self._pending_update.version}.")
        self._pending_update = None
        self._set_update_actions(False)

    def _download_and_install(self) -> None:
        if self._pending_update is None:
            return
        info = self._pending_update
        confirm = QMessageBox.question(
            self,
            "Install update?",
            (
                f"Download and install OpenBoson {info.version}?\n\n"
                "The Windows installer is currently unsigned. SmartScreen may warn "
                "before installation. The running app is not modified until you "
                "complete the installer.\n\n"
                f"Release: {info.release_url}"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._set_status(f"Downloading OpenBoson {info.version}…")
        self._set_update_actions(False)
        if self._check_now_btn is not None:
            self._check_now_btn.setEnabled(False)

        def _on_finished(result: object) -> None:
            self._on_download_finished(result)  # type: ignore[arg-type]

        self._download_thread, self._download_worker = start_download_thread(
            info,
            _on_finished,
        )

    def _on_download_finished(self, result: DownloadResult) -> None:
        if self._check_now_btn is not None:
            self._check_now_btn.setEnabled(True)
        if not result.ok or result.path is None:
            self._set_status(result.message)
            self._set_update_actions(self._pending_update is not None)
            return
        self._set_status(f"Verified download at {result.path}. Launching installer…")
        try:
            launch_installer(result.path)
            self._set_status(
                "Installer launched. Complete setup, then restart OpenBoson. "
                "Your study data under the data directory is preserved."
            )
            self._pending_update = None
            self._set_update_actions(False)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Could not launch installer: {exc}")
            self._set_update_actions(True)


# Back-compat helpers used by older tests/callers.
def load_settings_dict() -> dict:
    return asdict(load_settings())


# Alias expected by tests that monkeypatched module helpers historically.
save_settings_dict = save_settings
