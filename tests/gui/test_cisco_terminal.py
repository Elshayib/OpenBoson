"""pytest-qt coverage for CiscoTerminal keyboard behavior."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from openboson.gui.widgets.cisco_terminal import CiscoTerminal
from openboson.netsim.ios.device import DeviceRole, DeviceRuntime, InterfaceState
from openboson.netsim.ios.shell import Mode, OpenIOSShell


@pytest.fixture
def term(qtbot):
    d = DeviceRuntime(name="R1", role=DeviceRole.ROUTER, hostname="R1")
    d.interfaces["GigabitEthernet0/0"] = InterfaceState(name="GigabitEthernet0/0")
    shell = OpenIOSShell(d)
    w = CiscoTerminal(shell)
    qtbot.addWidget(w)
    w.show()
    return w


def test_terminal_object_name(term):
    assert term.objectName() == "CiscoTerminal"


def test_ctrl_z_ends_config(term, qtbot):
    term.type_line("enable")
    term.type_line("configure terminal")
    assert term.shell().mode == Mode.CONFIG
    qtbot.keyClick(term, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert term.shell().mode == Mode.ENABLE
    assert "R1#" in term.toPlainText()


def test_tab_completes_show(term, qtbot):
    term.type_line("enable")
    term._set_current_input("sh")
    qtbot.keyClick(term, Qt.Key.Key_Tab)
    assert term._current_input().startswith("show")


def test_mouse_selection_keeps_history_cursor(term, qtbot):
    term.type_line("enable")
    text = term.toPlainText()
    # Select from start of buffer (history) without forcing caret to input.
    c = term.textCursor()
    c.setPosition(0)
    c.setPosition(min(12, len(text)), QTextCursor.MoveMode.KeepAnchor)
    term.setTextCursor(c)
    assert term.textCursor().hasSelection()
    assert term.textCursor().position() < term._prompt_pos
