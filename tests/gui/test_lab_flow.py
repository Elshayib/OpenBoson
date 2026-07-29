"""GUI integration: OpenIOS lab flow through the main window."""

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
    # Terminal tabs for each device
    assert window._lab_session_page._tabs.count() >= 2


def test_cli_configure_and_finish_lab(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    page = window._lab_session_page

    # Configure R1 via OpenIOS
    page.type_on_device(
        "R1",
        "enable",
        "configure terminal",
        "hostname R1",
        "interface GigabitEthernet0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    )
    page._check_task()
    qtbot.wait(30)
    # Move to task 2 and configure SW1
    page._go_next()
    page.type_on_device(
        "SW1",
        "enable",
        "configure terminal",
        "hostname SW1",
        "vlan 10",
        "name USERS",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport mode trunk",
        "end",
    )
    page._check_task()
    qtbot.wait(30)
    page._finish_lab()
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab Result"
    labels = window._lab_result_page.findChildren(QLabel)
    assert any("ALL TASKS PASSED" in (l.text() or "") for l in labels)


def test_topology_canvas_renders(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    canvas = window._lab_session_page._canvas
    assert canvas._topology is not None
    canvas.repaint()


def test_lab_result_retake(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    sess = window._lab_session_page._session
    # Minimal finish
    window._lab_session_page._finish_lab()
    qtbot.wait(50)
    window._on_lab_retake(sess)
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab"


def test_click_topology_selects_console(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    page = window._lab_session_page
    page._on_device_clicked("SW1")
    # Active tab should mention SW1
    idx = page._tabs.currentIndex()
    assert "SW1" in page._tabs.tabText(idx)
