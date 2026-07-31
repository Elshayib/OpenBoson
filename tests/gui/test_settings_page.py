"""GUI test: Settings page loads, saves, and triggers theme change."""

import pytest
from PySide6.QtWidgets import QLabel

from openboson.gui.main_window import MainWindow
from openboson.settings_store import load_settings


@pytest.fixture
def fresh_settings(isolated_home):
    """Settings resolve under OPENBOSON_HOME via settings_store."""
    yield isolated_home


def test_settings_page_renders(fresh_settings, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Settings")
    page = mw._static_pages["Settings"]
    page.refresh()
    labels = [l.text() for l in page.findChildren(QLabel)]
    assert any("Data Directory" in t for t in labels)
    assert any("Theme" in t for t in labels)
    assert any("Content" in t for t in labels)
    assert any("Updates" in t for t in labels)
    assert not any("Default Exam Mode" in t for t in labels)


def test_settings_save_persists(fresh_settings, qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.select_page("Settings")
    page = mw._static_pages["Settings"]
    page.refresh()

    page._light_btn.click()
    page._save()

    cfg = load_settings()
    assert cfg.theme == "light"


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
