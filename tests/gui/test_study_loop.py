"""GUI tests for the study-loop coach CTAs (Dashboard + Stats)."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from openboson.gui.main_window import MainWindow
from openboson.stats_service import StudySuggestion

pytestmark = pytest.mark.usefixtures("isolated_home")

GOLD_LAB_ID = "ccna_branch_office_access"


@pytest.fixture
def main_window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    return mw


def _lab_suggestion() -> StudySuggestion:
    return StudySuggestion(
        kind="lab",
        title="Lab: Branch Office Access",
        domain_prefix="2.",
        topic_code="2.1",
        lab_id=GOLD_LAB_ID,
        cert_tag="ccna",
    )


def _practice_suggestion() -> StudySuggestion:
    return StudySuggestion(
        kind="practice",
        title="Practice domain 2",
        domain_prefix="2.",
        topic_code="2",
        lab_id=None,
        cert_tag="ccna",
    )


def test_dashboard_empty_state_tells_new_user_what_to_do(main_window):
    page = main_window._dashboard_page
    page.refresh()
    labels = [lbl.text() for lbl in page.findChildren(QLabel)]
    assert not any(t == "Welcome back" for t in labels)
    blob = " ".join(labels).lower()
    assert "ccna" in blob
    assert "gold lab" in blob
    buttons = [b.text().lower() for b in page.findChildren(QPushButton)]
    assert any("ccna" in t for t in buttons)
    assert any("gold lab" in t for t in buttons)


def test_dashboard_next_cta_starts_suggested_lab(main_window, qtbot, monkeypatch):
    suggestion = _lab_suggestion()
    monkeypatch.setattr(
        "openboson.gui.engine.suggest_next",
        lambda cert=None, labs=None: suggestion,
    )
    page = main_window._dashboard_page
    page.refresh()
    btn = page._suggest_btn
    assert btn is not None
    labels = [lbl.text() for lbl in page.findChildren(QLabel)]
    assert any(t.startswith("Next:") for t in labels)
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
    assert main_window.visible_page_label() == "Lab"


def test_stats_suggestion_cta_starts_lab(main_window, qtbot, monkeypatch):
    suggestion = _lab_suggestion()
    monkeypatch.setattr(
        "openboson.gui.engine.suggest_next",
        lambda cert=None, labs=None: suggestion,
    )
    main_window.select_page("Stats")
    page = main_window._static_pages["Stats"]
    page.refresh()
    btn = page._suggest_btn
    assert btn is not None
    assert btn.accessibleName() == "suggestNextBtn" or btn.objectName() == "suggestNextBtn"
    assert btn.text().startswith("Continue:")
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
    assert main_window.visible_page_label() == "Lab"


def test_apply_suggestion_practice_opens_practice(main_window):
    main_window.apply_suggestion(_practice_suggestion())
    assert main_window.visible_page_label() == "Practice"


def test_start_lab_by_id_opens_lab(main_window):
    main_window.start_lab_by_id(GOLD_LAB_ID)
    assert main_window.visible_page_label() == "Lab"


def test_start_lab_by_id_unknown_is_noop(main_window):
    main_window.start_lab_by_id("no-such-lab")
    assert main_window.visible_page_label() == "Dashboard"


def test_start_suggested_lab_opens_lab(main_window, monkeypatch):
    monkeypatch.setattr(
        "openboson.gui.engine.suggest_next",
        lambda cert=None, labs=None: _lab_suggestion(),
    )
    main_window.start_suggested_lab()
    assert main_window.visible_page_label() == "Lab"


def test_empty_state_gold_lab_button_starts_lab(main_window, qtbot):
    page = main_window._dashboard_page
    page.refresh()
    btn = next(b for b in page.findChildren(QPushButton) if "gold lab" in b.text().lower())
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
    assert main_window.visible_page_label() == "Lab"
