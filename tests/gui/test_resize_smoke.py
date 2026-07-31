"""Resize smoke tests — pages remain usable when the window shrinks."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QPushButton, QScrollArea

from openboson.gui.main_window import MainWindow
from openboson.gui.widgets.scroll_host import ScrollHost

pytestmark = pytest.mark.usefixtures("isolated_home")


@pytest.fixture
def main_window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.show()
    qtbot.waitExposed(mw)
    return mw


@pytest.mark.parametrize("size", [(960, 640), (1100, 700), (1280, 800)])
def test_window_resize_keeps_nav_visible(main_window, qtbot, size):
    w, h = size
    main_window.resize(w, h)
    qtbot.wait(50)
    assert main_window.width() >= 960
    assert main_window.height() >= 640
    # Sidebar nav buttons remain findable
    nav = [
        b
        for b in main_window.findChildren(QPushButton)
        if b.text() in {"Dashboard", "Practice", "Labs", "Stats", "Settings"}
    ]
    assert len(nav) == 5
    assert all(b.isVisible() for b in nav)


@pytest.mark.parametrize("label", ["Dashboard", "Practice", "Labs", "Stats", "Settings"])
def test_static_pages_have_scroll_host(main_window, label):
    main_window.select_page(label)
    page = main_window._static_pages[label]
    if label == "Practice":
        # Practice uses its own list scroll area, not ScrollHost
        scrolls = page.findChildren(QScrollArea)
        assert scrolls
    else:
        hosts = page.findChildren(ScrollHost)
        assert hosts, f"{label} should use ScrollHost"


def test_stats_and_settings_scroll_after_refresh(main_window, qtbot):
    main_window.resize(960, 640)
    for label in ("Stats", "Settings", "Labs"):
        main_window.select_page(label)
        page = main_window._static_pages[label]
        page.refresh()
        qtbot.wait(30)
        hosts = page.findChildren(ScrollHost)
        assert hosts
        assert hosts[0].widget() is not None


def test_exam_session_question_area_scrolls(main_window, qtbot):
    from pathlib import Path

    from openboson.bank_loader import load_exam_bank
    from openboson.exsim.session import ExamMode

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"
    bank = load_exam_bank(fixture)
    main_window.resize(960, 640)
    main_window.start_exam_from_list(bank, mode=ExamMode.EXAM)
    sess = main_window._session_page
    assert sess is not None
    scrolls = sess.findChildren(QScrollArea)
    # Grid scroll + question card scroll
    assert len(scrolls) >= 2
    assert sess._card_holder.isVisible()
    # Bookmark / mark live in the bottom bar (not crowded into the top bar)
    assert sess._bookmark_btn.isVisible()
    assert sess._mark_btn.isVisible()
    assert sess._finish.isVisible()
