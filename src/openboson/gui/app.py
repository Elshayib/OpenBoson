"""OpenBoson QApplication entrypoint.

``openboson gui`` calls ``run_gui()`` here. Tests use ``make_app()`` to get
a configured :class:`QApplication` without entering the event loop.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from openboson import __version__
from openboson.gui.main_window import MainWindow


def make_app(argv: list[str] | None = None) -> QApplication:
    """Create a configured :class:`QApplication` for OpenBoson."""
    if argv is None:
        argv = sys.argv
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv)
    app.setApplicationName("OpenBoson")
    app.setApplicationDisplayName("OpenBoson")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("OpenBoson")
    # Dark palette is shipped via styles.qss on the main window.
    return app


def run_gui() -> int:
    app = make_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_gui())
