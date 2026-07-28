"""Headless screenshot generator for the OpenBoson NetSim lab session page."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from openboson.gui.engine import load_available_labs
from openboson.gui.main_window import MainWindow

QSS = Path(__file__).resolve().parent / "src" / "openboson" / "gui" / "styles.qss"


def main() -> int:
    app = QApplication(sys.argv)
    if QSS.is_file():
        app.setStyleSheet(QSS.read_text(encoding="utf-8"))

    lab = load_available_labs()[0]
    win = MainWindow()
    win.start_lab_from_list(lab)
    win.resize(1280, 800)
    win.show()
    app.processEvents()

    out = Path("screens/lab_session.png")
    out.parent.mkdir(exist_ok=True)
    win.grab().save(str(out))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
