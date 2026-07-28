"""A compact exam timer / progress bar used in the exam session page."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class TimerBar(QWidget):
    """Shows elapsed or remaining time plus a question-progress bar.

    The timer ticks every second. ``on_timeout`` is emitted when the limit
    (if any) is reached.
    """

    def __init__(
        self, total_questions: int, limit_minutes: int = 0, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._total = total_questions
        self._limit_seconds = limit_minutes * 60
        self._elapsed = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._time_label = QLabel("00:00")
        self._time_label.setFixedWidth(70)
        layout.addWidget(self._time_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, total_questions)
        self._bar.setValue(0)
        layout.addWidget(self._bar, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._on_timeout = None

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def set_on_timeout(self, callback) -> None:
        self._on_timeout = callback

    def set_progress(self, answered: int) -> None:
        self._bar.setValue(min(answered, self._total))

    def _tick(self) -> None:
        self._elapsed += 1
        self._time_label.setText(self._format(self._elapsed))
        if self._limit_seconds and self._elapsed >= self._limit_seconds:
            self._timer.stop()
            if self._on_timeout:
                self._on_timeout()

    @staticmethod
    def _format(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def elapsed_seconds(self) -> int:
        return self._elapsed
