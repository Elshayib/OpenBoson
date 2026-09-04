"""First-run cert picker — CCNA vs ENCOR, once. No user account."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openboson.settings_store import AppSettings, load_settings, update_settings

SKIP_ONBOARDING_ENV = "OPENBOSON_SKIP_ONBOARDING"

CCNA_LABEL = "Study CCNA 200-301"
ENCOR_LABEL = "Study ENCOR 350-401"


def should_prompt_first_run(cfg: AppSettings | None = None) -> bool:
    """True when a stranger should see the CCNA / ENCOR picker."""
    if os.environ.get(SKIP_ONBOARDING_ENV) == "1":
        return False
    if cfg is None:
        cfg = load_settings()
    return not cfg.onboarding_complete


def persist_first_run_choice(cert: str) -> AppSettings:
    """Mark onboarding done and store the preferred cert tag."""
    if cert not in ("ccna", "ccnp"):
        raise ValueError(f"Unknown cert track: {cert!r}")
    return update_settings(onboarding_complete=True, preferred_cert=cert)


class FirstRunDialog(QDialog):
    """Modal with two equal choices: CCNA 200-301 or ENCOR 350-401."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FirstRunDialog")
        self.setWindowTitle("Welcome to OpenBoson")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(420)
        self._selected_cert: str | None = None

        if parent is not None and parent.styleSheet():
            self.setStyleSheet(parent.styleSheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(10)

        title = QLabel("Welcome to OpenBoson")
        title.setProperty("role", "h1")
        title.setWordWrap(True)
        root.addWidget(title)

        blurb = QLabel(
            "Local study for CCNA and CCNP. Pick a track to start — "
            "you can switch later in Practice."
        )
        blurb.setProperty("role", "muted")
        blurb.setWordWrap(True)
        root.addWidget(blurb)

        root.addSpacing(8)

        self._ccna_btn = QPushButton(CCNA_LABEL)
        self._ccna_btn.setObjectName("CertChoice")
        self._ccna_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ccna_btn.setAccessibleName(CCNA_LABEL)
        self._ccna_btn.clicked.connect(lambda: self._choose("ccna"))
        root.addWidget(self._ccna_btn)

        self._encor_btn = QPushButton(ENCOR_LABEL)
        self._encor_btn.setObjectName("CertChoice")
        self._encor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._encor_btn.setAccessibleName(ENCOR_LABEL)
        self._encor_btn.clicked.connect(lambda: self._choose("ccnp"))
        root.addWidget(self._encor_btn)

    def selected_cert(self) -> str | None:
        return self._selected_cert

    def _choose(self, cert: str) -> None:
        self._selected_cert = cert
        self.accept()
