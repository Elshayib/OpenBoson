"""Smoke test for the PySide6 main window."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton

from openboson.gui.main_window import MainWindow
from openboson.gui.widgets.first_run import (
    CCNA_LABEL,
    ENCOR_LABEL,
    FirstRunDialog,
    persist_first_run_choice,
    should_prompt_first_run,
)
from openboson.settings_store import load_settings, update_settings

pytestmark = pytest.mark.usefixtures("isolated_home")


@pytest.fixture
def main_window(qtbot, isolated_home):
    update_settings(onboarding_complete=True)
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
    assert "#f7f6f3" in style
    assert "#TopBar" in style
    assert "QPushButton#Primary" in style


def test_light_theme_stylesheet_has_no_dark_chrome(main_window):
    main_window.apply_theme("light")
    style = main_window.styleSheet()
    assert "#f7f6f3" in style
    assert "#0f766e" in style
    assert "#0f1420" not in style
    assert "#MatchSlot" in style
    assert "background-color: #161b22" not in style
    assert "#TopBar" in style
    assert "QPushButton#Primary" in style
    # Match slots should follow theme QSS, not hardcoded dark inline styles
    from openboson.gui.widgets.question_card import _MatchSlot

    slot = _MatchSlot("VLAN")
    assert slot.styleSheet() == ""
    assert slot.property("matchState") == "idle"

    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication

    pal = QApplication.instance().palette()
    assert pal.color(QPalette.ColorRole.Window).name() == "#f7f6f3"
    assert pal.color(QPalette.ColorRole.Base).name() == "#ffffff"


def test_dark_theme_stylesheet_still_available(main_window):
    main_window.apply_theme("dark")
    style = main_window.styleSheet()
    assert "#0f1420" in style
    assert "#TopBar" in style
    assert "#f7f6f3" not in style


def test_window_icon_is_ob_monogram(main_window):
    assert not main_window.windowIcon().isNull()


def test_premium_qss_has_type_scale_and_cards(main_window):
    style = main_window.styleSheet()
    assert 'QLabel[role="h1"]' in style
    assert "font-size: 22px" in style
    assert "border-radius: 12px" in style
    assert "#TeachingFeedback" in style
    assert "#ExplanationBody" in style
    assert "QPushButton#CertChoice" in style
    main_window.apply_theme("dark")
    dark = main_window.styleSheet()
    assert "border-radius: 12px" in dark
    assert 'QLabel[role="h2"]' in dark
    # Checked nav is a hairline pill, not a flat #2f81f7 slab.
    checked = dark.split("#TopBar QPushButton:checked")[1][:180]
    assert "#2f81f7" not in checked
    assert "#1a2740" in checked


def test_should_prompt_first_run_respects_flag_and_env(isolated_home, monkeypatch):
    monkeypatch.delenv("OPENBOSON_SKIP_ONBOARDING", raising=False)
    update_settings(onboarding_complete=False)
    assert should_prompt_first_run() is True
    update_settings(onboarding_complete=True)
    assert should_prompt_first_run() is False
    update_settings(onboarding_complete=False)
    monkeypatch.setenv("OPENBOSON_SKIP_ONBOARDING", "1")
    assert should_prompt_first_run() is False


def test_first_run_dialog_has_two_cert_choices(qtbot, isolated_home):
    dlg = FirstRunDialog()
    qtbot.addWidget(dlg)
    labels = [b.text() for b in dlg.findChildren(QPushButton)]
    assert CCNA_LABEL in labels
    assert ENCOR_LABEL in labels
    qtbot.mouseClick(dlg._ccna_btn, Qt.MouseButton.LeftButton)
    assert dlg.selected_cert() == "ccna"
    assert dlg.result() == QDialog.DialogCode.Accepted


def test_first_run_encor_choice_and_persist(qtbot, isolated_home, monkeypatch):
    monkeypatch.delenv("OPENBOSON_SKIP_ONBOARDING", raising=False)
    dlg = FirstRunDialog()
    qtbot.addWidget(dlg)
    qtbot.mouseClick(dlg._encor_btn, Qt.MouseButton.LeftButton)
    assert dlg.selected_cert() == "ccnp"
    persist_first_run_choice("ccnp")
    cfg = load_settings()
    assert cfg.onboarding_complete is True
    assert cfg.preferred_cert == "ccnp"
    assert should_prompt_first_run() is False


def test_onboarded_window_does_not_open_first_run(main_window, qtbot, monkeypatch):
    opened: list[bool] = []

    def _fake_exec(self):
        opened.append(True)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(FirstRunDialog, "exec", _fake_exec)
    main_window.show()
    qtbot.waitExposed(main_window)
    qtbot.wait(30)
    main_window._maybe_show_first_run()
    assert opened == []


def test_first_run_choice_navigates_to_practice(qtbot, isolated_home, monkeypatch):
    monkeypatch.delenv("OPENBOSON_SKIP_ONBOARDING", raising=False)
    update_settings(onboarding_complete=False)

    class _FakeDlg:
        def __init__(self, parent=None):
            self._parent = parent

        def exec(self):
            return QDialog.DialogCode.Accepted

        def selected_cert(self):
            return "ccna"

    monkeypatch.setattr(
        "openboson.gui.widgets.first_run.FirstRunDialog",
        _FakeDlg,
    )
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw._maybe_show_first_run()
    cfg = load_settings()
    assert cfg.onboarding_complete is True
    assert cfg.preferred_cert == "ccna"
    assert mw.visible_page_label() == "Practice"
