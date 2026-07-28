"""Allows ``python -m openboson.gui`` to launch the GUI."""

from openboson.gui.app import run_gui

if __name__ == "__main__":
    raise SystemExit(run_gui())
