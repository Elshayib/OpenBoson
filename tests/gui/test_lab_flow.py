"""GUI integration test: full NetSim lab flow through the main window."""

import pytest
from PySide6.QtWidgets import QFrame, QLabel

from openboson.gui.engine import load_available_labs
from openboson.gui.main_window import MainWindow


@pytest.fixture
def window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    return mw


def test_labs_page_lists_demo_lab(window):
    window.select_page("Labs")
    page = window._labs_page
    cards = page.findChildren(QFrame)
    assert len(cards) >= 1


def test_start_lab_shows_session(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab"
    assert window._lab_session_page.current_task_id() is not None


def test_submit_and_finish_lab(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    sess = window._lab_session_page._session
    # Submit each task's expected config (engine advances per submit).
    for t in list(lab.tasks):
        window._lab_session_page.submit_config(t.expected_config)
    qtbot.wait(50)
    window._lab_session_page._finish_lab()
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab Result"
    # Should report all tasks passed.
    labels = window._lab_result_page.findChildren(QLabel)
    assert any("ALL TASKS PASSED" in (l.text() or "") for l in labels)


def test_topology_canvas_renders(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    canvas = window._lab_session_page._canvas
    # Just ensure it doesn't raise and has a topology set.
    assert canvas._topology is not None
    canvas.repaint()


def test_lab_result_retake(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    sess = window._lab_session_page._session
    for t in list(lab.tasks):
        window._lab_session_page.submit_config(t.expected_config)
    window._lab_session_page._finish_lab()
    qtbot.wait(50)
    window._on_lab_retake(sess)
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab"
