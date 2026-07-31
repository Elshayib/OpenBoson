"""GUI integration: gold lab OpenIOS flow."""

import pytest
from PySide6.QtWidgets import QFrame, QLabel

from openboson.gui.engine import load_available_labs
from openboson.gui.main_window import MainWindow


pytestmark = pytest.mark.usefixtures("isolated_home")


@pytest.fixture
def window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    return mw


def test_labs_page_lists_gold_lab(window):
    window.select_page("Labs")
    page = window._labs_page
    cards = page.findChildren(QFrame)
    assert len(cards) >= 1


def test_start_lab_shows_four_consoles(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab"
    assert window._lab_session_page._tabs.count() == 4


def test_gold_lab_full_cli_path(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    page = window._lab_session_page

    # t1 R1
    page.type_on_device(
        "R1",
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    )
    page._check_task()
    assert page._session.grades["t1"].is_correct

    # t2 SW1
    page._go_next()
    page.type_on_device(
        "SW1",
        "enable",
        "configure terminal",
        "vlan 10",
        "name USERS",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport mode trunk",
        "exit",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 10",
        "exit",
        "interface GigabitEthernet0/3",
        "switchport mode access",
        "switchport access vlan 10",
        "end",
    )
    page._check_task()
    assert page._session.grades["t2"].is_correct

    # t3 PCs
    page._go_next()
    page.type_on_device("PC1", "ip address 10.10.10.10 255.255.255.0")
    page.type_on_device("PC2", "ip address 10.10.10.20 255.255.255.0")
    page._check_task()
    assert page._session.grades["t3"].is_correct

    # t4 verify configs still hold
    page._go_next()
    page._check_task()
    assert page._session.grades["t4"].is_correct

    page._finish_lab()
    qtbot.wait(50)
    assert window.visible_page_label() == "Lab Result"
    labels = window._lab_result_page.findChildren(QLabel)
    assert any("ALL TASKS PASSED" in (l.text() or "") for l in labels)


def test_fail_feedback_has_no_ios_commands(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(30)
    page = window._lab_session_page
    page._check_task()
    fb = page._session.grades["t1"].feedback.lower()
    assert "no shutdown" not in fb
    assert "configure" not in fb
    assert fb  # coachy


def test_topology_canvas_renders(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    assert window._lab_session_page._canvas._topology is not None


def test_click_topology_selects_console(window, qtbot):
    lab = load_available_labs()[0]
    window.start_lab_from_list(lab)
    qtbot.wait(50)
    page = window._lab_session_page
    page._on_device_clicked("PC1")
    idx = page._tabs.currentIndex()
    assert "PC1" in page._tabs.tabText(idx)
