"""Smoke test for the PySide6 main window."""

import pytest

from openboson.gui.main_window import MainWindow

pytestmark = pytest.mark.usefixtures("isolated_home")


@pytest.fixture
def main_window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    return mw


def test_main_window_has_expected_pages(main_window):
    expected = {"Dashboard", "Practice", "Labs", "Stats", "Settings"}
    assert set(main_window._static_pages.keys()) == expected


def test_main_window_defaults_to_dashboard(main_window):
    assert main_window.visible_page_label() == "Dashboard"


def test_select_navigates_to_practice(main_window):
    main_window.select_page("Practice")
    assert main_window.visible_page_label() == "Practice"


def test_select_navigates_to_labs(main_window):
    main_window.select_page("Labs")
    assert main_window.visible_page_label() == "Labs"


def test_select_all_pages_round_trip(main_window):
    for label in ["Practice", "Labs", "Stats", "Settings", "Dashboard"]:
        main_window.select_page(label)
        assert main_window.visible_page_label() == label


def test_unknown_page_raises(main_window):
    with pytest.raises(KeyError):
        main_window.select_page("Nonexistent")


def test_style_sheet_is_applied(main_window):
    style = main_window.styleSheet()
    assert "#0f1420" in style
    assert "#Sidebar" in style
    assert "QPushButton#Primary" in style


def test_light_theme_stylesheet_has_no_dark_chrome(main_window):
    main_window.apply_theme("light")
    style = main_window.styleSheet()
    assert "#f5f7fb" in style
    assert "#0f1420" not in style
    assert "#MatchSlot" in style
    assert "background-color: #161b22" not in style
    assert "#Sidebar" in style
    assert "QPushButton#Primary" in style
    # Match slots should follow theme QSS, not hardcoded dark inline styles
    from openboson.gui.widgets.question_card import _MatchSlot

    slot = _MatchSlot("VLAN")
    assert slot.styleSheet() == ""
    assert slot.property("matchState") == "idle"

    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication

    pal = QApplication.instance().palette()
    assert pal.color(QPalette.ColorRole.Window).name() == "#f5f7fb"
    assert pal.color(QPalette.ColorRole.Base).name() == "#ffffff"
