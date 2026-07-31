"""A compact exam timer / progress bar used in the exam session page."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class TimerBar(QWidget):
    """Shows remaining (or elapsed) time plus a question-progress bar.

    When ``limit_minutes`` > 0 the label counts **down**. ``on_timeout`` is
    called when the limit is reached. Pause freezes ticks without resetting
    remaining time.
    """

    def __init__(
        self, total_questions: int, limit_minutes: int = 0, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._total = max(total_questions, 1)
        self._limit_seconds = limit_minutes * 60
        self._elapsed = 0
        self._countdown = self._limit_seconds > 0
        self._paused = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._time_label = QLabel(self._format(self._limit_seconds if self._countdown else 0))
        self._time_label.setFixedWidth(80)
        layout.addWidget(self._time_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, self._total)
        self._bar.setValue(0)
        layout.addWidget(self._bar, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._on_timeout = None

    def start(self) -> None:
        self._paused = False
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def pause(self) -> None:
        """Freeze the countdown without clearing remaining time."""
        self._paused = True
        self._timer.stop()

    def resume(self) -> None:
        """Continue ticking from the frozen remaining / elapsed value."""
        if self._paused or not self._timer.isActive():
            self._paused = False
            self._timer.start()

    def is_paused(self) -> bool:
        return self._paused

    def set_on_timeout(self, callback) -> None:
        self._on_timeout = callback

    def set_progress(self, answered: int) -> None:
        self._bar.setValue(min(answered, self._total))

    def set_remaining(self, seconds: int | None) -> None:
        """Restore countdown from a persisted remaining value."""
        if seconds is None or not self._countdown:
            return
        seconds = max(0, int(seconds))
        self._elapsed = max(0, self._limit_seconds - seconds)
        self._time_label.setText(self._format(seconds))

    def _tick(self) -> None:
        if self._paused:
            return
        self._elapsed += 1
        if self._countdown:
            remaining = max(0, self._limit_seconds - self._elapsed)
            self._time_label.setText(self._format(remaining))
            if remaining <= 0:
                self._timer.stop()
                if self._on_timeout:
                    self._on_timeout()
        else:
            self._time_label.setText(self._format(self._elapsed))

    @staticmethod
    def _format(seconds: int) -> str:
        m, s = divmod(max(0, seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def elapsed_seconds(self) -> int:
        return self._elapsed

    def remaining_seconds(self) -> int | None:
        if not self._countdown:
            return None
        return max(0, self._limit_seconds - self._elapsed)
