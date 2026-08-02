"""Cisco-like terminal widget — real line editing against OpenIOS shells."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from openboson.netsim.ios.shell import Mode, OpenIOSShell


class CiscoTerminal(QPlainTextEdit):
    """Interactive terminal bound to an ``OpenIOSShell`` (or HostShell).

    - History is read-only for typing; mouse selection/copy is allowed.
    - Enter feeds the line to the shell and appends output + new prompt.
    - Ctrl+C prints ``^C`` and redisplays the prompt.
    - Ctrl+Z sends ``end`` while in a config mode (IOS muscle memory).
    - Ctrl+L clears the screen and redraws the prompt.
    - Tab inserts completion candidates; Space/Enter/q continue ``--More--``.
    """

    commandSubmitted = Signal(str)

    def __init__(self, shell: OpenIOSShell | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CiscoTerminal")
        self._shell = shell
        self._prompt = ">"
        self._prompt_pos = 0
        self._hist: list[str] = []
        self._hist_idx = 0
        self._more_mode = False

        font = QFont("Cascadia Mono")
        if not font.exactMatch():
            font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.setFont(font)

        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setTabChangesFocus(False)

        if shell is not None:
            self.bind_shell(shell)

    def bind_shell(self, shell: OpenIOSShell) -> None:
        self._shell = shell
        self._more_mode = False
        self.clear()
        banner = shell.banner()
        self._append_raw(banner)
        self._prompt = shell.prompt()
        self._prompt_pos = len(self.toPlainText())
        self._move_cursor_end()

    def shell(self) -> OpenIOSShell | None:
        return self._shell

    def clear_screen(self) -> None:
        """Clear buffer and redraw the current prompt (Ctrl+L / cls)."""
        if self._shell is None:
            return
        self.clear()
        self._more_mode = False
        self._prompt = self._shell.prompt()
        self._append_raw(self._prompt)
        self._prompt_pos = len(self.toPlainText())
        self._move_cursor_end()

    # -----/ Input handling /-----
    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        if self._shell is None:
            return

        key = e.key()
        mods = e.modifiers()

        # --More-- pager: Space / Enter / q without requiring a full typed line.
        if self._more_mode and not (mods & Qt.KeyboardModifier.ControlModifier):
            if key == Qt.Key.Key_Space:
                self._set_current_input(" ")
                self._submit()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._set_current_input("")
                self._submit()
                return
            if key == Qt.Key.Key_Q:
                self._set_current_input("q")
                self._submit()
                return

        if key == Qt.Key.Key_C and mods & Qt.KeyboardModifier.ControlModifier:
            # With a selection, allow default copy; otherwise IOS ^C interrupt.
            if self.textCursor().hasSelection():
                super().keyPressEvent(e)
                return
            self._more_mode = False
            self._append_raw("^C\n" + self._shell.prompt())
            self._prompt = self._shell.prompt()
            self._prompt_pos = len(self.toPlainText())
            self._move_cursor_end()
            return

        if key == Qt.Key.Key_Z and mods & Qt.KeyboardModifier.ControlModifier:
            if self._in_config_mode():
                self._set_current_input("end")
                self._submit()
            return

        if key == Qt.Key.Key_L and mods & Qt.KeyboardModifier.ControlModifier:
            self.clear_screen()
            return

        # Typing keys must stay on the input line; selection/navigation can roam.
        if self._is_editing_key(key, mods) and self.textCursor().position() < self._prompt_pos:
            self._move_cursor_end()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.textCursor().position() < self._prompt_pos:
                self._move_cursor_end()
            self._submit()
            return

        if key == Qt.Key.Key_Tab:
            if self.textCursor().position() < self._prompt_pos:
                self._move_cursor_end()
            self._tab_complete()
            return

        if key == Qt.Key.Key_Up:
            if self.textCursor().position() < self._prompt_pos:
                self._move_cursor_end()
            self._history(-1)
            return
        if key == Qt.Key.Key_Down:
            if self.textCursor().position() < self._prompt_pos:
                self._move_cursor_end()
            self._history(1)
            return

        if key == Qt.Key.Key_Backspace:
            if self.textCursor().position() <= self._prompt_pos:
                return
            super().keyPressEvent(e)
            return

        if key == Qt.Key.Key_Left:
            if self.textCursor().position() <= self._prompt_pos:
                return
            super().keyPressEvent(e)
            return

        if key == Qt.Key.Key_Home:
            if self.textCursor().position() < self._prompt_pos:
                return
            c = self.textCursor()
            c.setPosition(self._prompt_pos)
            self.setTextCursor(c)
            return

        if key == Qt.Key.Key_Delete and self.textCursor().position() < self._prompt_pos:
            return

        super().keyPressEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        # Allow selecting history for copy; do not force caret to input on click.
        super().mousePressEvent(e)

    def insertFromMimeData(self, source) -> None:  # noqa: N802
        """Paste only into the current input line (multi-line → feed each)."""
        if self._shell is None:
            return
        text = source.text()
        if not text:
            return
        if self.textCursor().position() < self._prompt_pos:
            self._move_cursor_end()
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if lines:
            self.insertPlainText(lines[0])
        for extra in lines[1:]:
            self._submit()
            if extra:
                self.insertPlainText(extra)

    # -----/ Internals /-----
    def _in_config_mode(self) -> bool:
        mode = getattr(self._shell, "mode", None)
        if mode is None:
            return False
        return mode in {
            Mode.CONFIG,
            Mode.CONFIG_IF,
            Mode.CONFIG_VLAN,
            Mode.CONFIG_LINE,
            Mode.CONFIG_ROUTER,
        }

    @staticmethod
    def _is_editing_key(key: int, mods: Qt.KeyboardModifier) -> bool:
        if mods & Qt.KeyboardModifier.ControlModifier:
            return key in {
                Qt.Key.Key_V,
                Qt.Key.Key_X,
                Qt.Key.Key_Backspace,
                Qt.Key.Key_Delete,
            }
        if key in (
            Qt.Key.Key_Backspace,
            Qt.Key.Key_Delete,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            return True
        # Printable / text entry
        return key < 0x01000000  # Qt non-special keys

    def _current_input(self) -> str:
        full = self.toPlainText()
        return full[self._prompt_pos :]

    def _set_current_input(self, text: str) -> None:
        full = self.toPlainText()[: self._prompt_pos] + text
        self.setPlainText(full)
        self._move_cursor_end()

    def _submit(self) -> None:
        assert self._shell is not None
        line = self._current_input()
        self.commandSubmitted.emit(line)
        if line.strip() and not self._more_mode:
            self._hist.append(line)
        self._hist_idx = len(self._hist)
        self._append_raw("\n")
        result = self._shell.feed(line)
        if result.output:
            out = result.output
            if not out.endswith("\n") and "--More--" not in out:
                out += "\n"
            self._append_raw(out)
        self._more_mode = "--More--" in (result.output or "")
        self._prompt = self._shell.prompt()
        text = self.toPlainText()
        if self._more_mode:
            # Pager waits for Space / Enter / q — no normal prompt yet.
            self._prompt_pos = len(text)
        elif not text.endswith(self._prompt):
            self._append_raw(self._prompt)
            self._prompt_pos = len(self.toPlainText())
        else:
            self._prompt_pos = len(self.toPlainText())
        self._move_cursor_end()

        # Host ``cls`` clears with ANSI — honor by wiping the widget.
        if "\x1b[2J" in (result.output or ""):
            self.clear_screen()

    def _tab_complete(self) -> None:
        assert self._shell is not None
        partial = self._current_input()
        cands = self._shell.complete(partial)
        if not cands:
            return
        tokens = partial.split()
        if len(cands) == 1:
            if partial.endswith(" ") or not tokens:
                self._set_current_input(partial + cands[0] + " ")
            else:
                tokens[-1] = cands[0]
                self._set_current_input(" ".join(tokens) + " ")
        else:
            self._append_raw("\n" + "  ".join(cands) + "\n" + self._prompt + partial)
            self._prompt_pos = len(self.toPlainText()) - len(partial)
            self._move_cursor_end()

    def _history(self, delta: int) -> None:
        if not self._hist:
            return
        self._hist_idx = max(0, min(len(self._hist), self._hist_idx + delta))
        if self._hist_idx == len(self._hist):
            self._set_current_input("")
        else:
            self._set_current_input(self._hist[self._hist_idx])

    def _append_raw(self, text: str) -> None:
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def _move_cursor_end(self) -> None:
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(c)

    def type_line(self, line: str) -> str:
        """Test helper: type a full line and submit. Returns shell output."""
        self._set_current_input(line)
        before = self.toPlainText()
        self._submit()
        after = self.toPlainText()
        return after[len(before) :]
