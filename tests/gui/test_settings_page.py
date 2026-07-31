"""GUI test: Settings page loads, saves, and triggers theme change."""

import pytest
from PySide6.QtWidgets import QLabel

from openboson.gui.main_window import MainWindow


@pytest.fixture
def fresh_settings(tmp_path, monkeypatch):
    """Redirect settings to a temp dir so tests don't touch real data."""
    monkeypatch.setenv("OPENBOSON_HOME", str(tmp_path))
    from openboson.gui.pages import settings_page

    monkeypatch.setattr(settings_page, "_SETTINGS_FILE", tmp_path / "settings.json")
    yield tmp_path


def test_settings_page_renders(fresh_settings, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Settings")
    page = mw._static_pages["Settings"]
    page.refresh()
    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any("Data Directory" in t for t in labels)
    assert any("Theme" in t for t in labels)
    assert not any("Default Exam Mode" in t for t in labels)


def test_settings_save_persists(fresh_settings, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Settings")
    page = mw._static_pages["Settings"]
    page.refresh()

    page._light_btn.click()
    page._save()

    from openboson.gui.pages.settings_page import load_settings

    cfg = load_settings()
    assert cfg["theme"] == "light"


def test_settings_theme_change_callback(fresh_settings, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Settings")
    page = mw._static_pages["Settings"]
    page.refresh()

    triggered = []
    page.set_on_theme_change(lambda t: triggered.append(t))

    page._light_btn.click()
    page._save()
    assert triggered == ["light"]
