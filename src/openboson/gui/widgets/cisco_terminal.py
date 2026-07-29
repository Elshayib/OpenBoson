"""Cisco-like terminal widget — real line editing against OpenIOS shells."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from openboson.netsim.ios.shell import OpenIOSShell


class CiscoTerminal(QPlainTextEdit):
    """Interactive terminal bound to an ``OpenIOSShell``.

    - History is read-only; only the current input line is editable.
    - Enter feeds the line to the shell and appends output + new prompt.
    - Ctrl+C prints ``^C`` and redisplays the prompt.
    - Tab inserts the first completion candidate when unique-ish.
    """

    commandSubmitted = Signal(str)  # raw command line (for logging/tests)

    def __init__(self, shell: OpenIOSShell | None = None, parent=None) -> None:
        super().__init__(parent)
        self._shell = shell
        self._prompt = ">"
        self._prompt_pos = 0  # cursor position where current input starts
        self._hist: list[str] = []
        self._hist_idx = 0

        font = QFont("Cascadia Mono")
        if not font.exactMatch():
            font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.setFont(font)

        self.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #0c0f14;
                color: #c8facc;
                border: 1px solid #1e2a3a;
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #1f6feb;
            }
            """
        )
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setTabChangesFocus(False)

        if shell is not None:
            self.bind_shell(shell)

    def bind_shell(self, shell: OpenIOSShell) -> None:
        self._shell = shell
        self.clear()
        banner = shell.banner()
        self._append_raw(banner)
        self._prompt = shell.prompt()
        # banner already ends with prompt
        self._prompt_pos = len(self.toPlainText())
        self._move_cursor_end()

    def shell(self) -> OpenIOSShell | None:
        return self._shell

    # -----/ Input handling /-----
    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        if self._shell is None:
            return

        # Keep cursor in the editable region.
        if self.textCursor().position() < self._prompt_pos:
            self._move_cursor_end()

        key = e.key()
        mods = e.modifiers()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._submit()
            return

        if key == Qt.Key.Key_C and mods & Qt.KeyboardModifier.ControlModifier:
            self._append_raw("^C\n" + self._shell.prompt())
            self._prompt = self._shell.prompt()
            self._prompt_pos = len(self.toPlainText())
            self._move_cursor_end()
            return

        if key == Qt.Key.Key_Tab:
            self._tab_complete()
            return

        if key == Qt.Key.Key_Up:
            self._history(-1)
            return
        if key == Qt.Key.Key_Down:
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
            c = self.textCursor()
            c.setPosition(self._prompt_pos)
            self.setTextCursor(c)
            return

        # Block edits that would mangle history (Ctrl+X etc. simplified).
        if key in (Qt.Key.Key_Delete,) and self.textCursor().position() < self._prompt_pos:
            return

        super().keyPressEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        super().mousePressEvent(e)
        if self.textCursor().position() < self._prompt_pos:
            self._move_cursor_end()

    def insertFromMimeData(self, source) -> None:  # noqa: N802
        """Paste only into the current input line (multi-line → feed each)."""
        if self._shell is None:
            return
        text = source.text()
        if not text:
            return
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        # First line goes into current buffer; subsequent lines auto-submit.
        if lines:
            self.insertPlainText(lines[0])
        for extra in lines[1:]:
            self._submit()
            if extra:
                self.insertPlainText(extra)

    # -----/ Internals /-----
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
        if line.strip():
            self._hist.append(line)
        self._hist_idx = len(self._hist)
        # Echo already on screen; just newline then output.
        self._append_raw("\n")
        result = self._shell.feed(line)
        if result.output:
            out = result.output
            if not out.endswith("\n"):
                out += "\n"
            # If help left prompt at end already, avoid double prompt later.
            self._append_raw(out)
        self._prompt = self._shell.prompt()
        # Help handler may already include prompt at end.
        text = self.toPlainText()
        if not text.endswith(self._prompt):
            self._append_raw(self._prompt)
        self._prompt_pos = len(self.toPlainText())
        self._move_cursor_end()

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
            # Show candidates like IOS
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

    # Test helpers
    def type_line(self, line: str) -> str:
        """Test helper: type a full line and submit. Returns shell output."""
        self._set_current_input(line)
        before = self.toPlainText()
        self._submit()
        after = self.toPlainText()
        return after[len(before) :]
