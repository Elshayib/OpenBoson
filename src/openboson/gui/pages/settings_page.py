"""Settings page — data dir, default exam mode, theme toggle."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from openboson.config import settings


_SETTINGS_FILE = settings.data_dir / "settings.json"

_DEFAULTS = {
    "default_exam_mode": "timed",
    "theme": "dark",
}


def load_settings() -> dict:
    """Load user settings from disk, merged with defaults."""
    merged = dict(_DEFAULTS)
    if _SETTINGS_FILE.is_file():
        try:
            merged.update(json.loads(_SETTINGS_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return merged


def save_settings(data: dict) -> None:
    """Persist user settings to disk."""
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))


class SettingsPage(QWidget):
    title = "Settings"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self._on_theme_change = None

    def set_on_theme_change(self, cb) -> None:
        self._on_theme_change = cb

    def refresh(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        header = QLabel("Settings")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        cfg = load_settings()

        # --- Data directory ---
        dir_card = QFrame()
        dir_card.setObjectName("Card")
        dl = QVBoxLayout(dir_card)
        dl.setContentsMargins(18, 16, 18, 16)
        dl.addWidget(self._label("Data Directory", "h2"))
        path_lbl = QLabel(str(settings.data_dir))
        path_lbl.setProperty("role", "muted")
        path_lbl.setWordWrap(True)
        dl.addWidget(path_lbl)
        open_btn = QPushButton("Open in File Explorer")
        open_btn.setObjectName("Secondary")
        open_btn.clicked.connect(self._open_data_dir)
        dl.addWidget(open_btn)
        self._layout.addWidget(dir_card)

        # --- Default exam mode ---
        mode_card = QFrame()
        mode_card.setObjectName("Card")
        ml = QVBoxLayout(mode_card)
        ml.setContentsMargins(18, 16, 18, 16)
        ml.addWidget(self._label("Default Exam Mode", "h2"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Timed (exam simulation)", "timed")
        self._mode_combo.addItem("Study (instant feedback)", "study")
        idx = 0 if cfg.get("default_exam_mode", "timed") == "timed" else 1
        self._mode_combo.setCurrentIndex(idx)
        ml.addWidget(self._mode_combo)
        self._layout.addWidget(mode_card)

        # --- Theme ---
        theme_card = QFrame()
        theme_card.setObjectName("Card")
        tl = QVBoxLayout(theme_card)
        tl.setContentsMargins(18, 16, 18, 16)
        tl.addWidget(self._label("Theme", "h2"))
        self._theme_group = QButtonGroup(self)
        self._dark_btn = QRadioButton("Dark")
        self._light_btn = QRadioButton("Light")
        self._theme_group.addButton(self._dark_btn)
        self._theme_group.addButton(self._light_btn)
        if cfg.get("theme", "dark") == "light":
            self._light_btn.setChecked(True)
        else:
            self._dark_btn.setChecked(True)
        row = QHBoxLayout()
        row.addWidget(self._dark_btn)
        row.addWidget(self._light_btn)
        row.addStretch()
        tl.addLayout(row)
        self._layout.addWidget(theme_card)

        # --- Save ---
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        self._layout.addWidget(save_btn)

        self._layout.addStretch()

    def _label(self, text: str, role: str = "muted") -> QLabel:
        l = QLabel(text)
        l.setProperty("role", role)
        return l

    def _open_data_dir(self) -> None:
        import subprocess
        import sys
        path = str(settings.data_dir)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _save(self) -> None:
        cfg = load_settings()
        cfg["default_exam_mode"] = self._mode_combo.currentData()
        cfg["theme"] = "light" if self._light_btn.isChecked() else "dark"
        save_settings(cfg)
        if self._on_theme_change:
            self._on_theme_change(cfg["theme"])
