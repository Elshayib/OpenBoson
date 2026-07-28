"""NetSim lab session page — instructions, terminal-style config input, topology."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.netsim.lab_schema import LabBank
from openboson.netsim.session import LabSession
from openboson.gui.engine import finish_and_score_lab, start_lab_session
from openboson.gui.widgets.topology_canvas import TopologyCanvas


class LabSessionPage(QWidget):
    """Drives a guided lab: task instructions, config editor, grading, nav."""

    title = "Lab"

    def __init__(self) -> None:
        super().__init__()
        self._session: LabSession | None = None
        self._on_result: callable | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left: instructions + config editor + actions
        left = QVBoxLayout()
        left.setContentsMargins(24, 16, 16, 16)
        left.setSpacing(12)

        self._task_header = QLabel("")
        self._task_header.setProperty("role", "h2")
        left.addWidget(self._task_header)

        self._instructions = QTextBrowser()
        self._instructions.setOpenExternalLinks(False)
        self._instructions.setMinimumHeight(80)
        self._instructions.setFrameShape(QFrame.Shape.NoFrame)
        left.addWidget(self._instructions)

        editor_label = QLabel("Configuration")
        editor_label.setProperty("role", "muted")
        left.addWidget(editor_label)
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("configure terminal\n...\nend")
        self._editor.setMinimumHeight(180)
        left.addWidget(self._editor, 1)

        actions = QHBoxLayout()
        self._prev = QPushButton("‹ Previous")
        self._prev.setObjectName("Secondary")
        self._prev.clicked.connect(self._go_prev)
        self._submit = QPushButton("Submit & Grade")
        self._submit.setObjectName("Primary")
        self._submit.clicked.connect(self._submit_task)
        self._next = QPushButton("Next ›")
        self._next.setObjectName("Secondary")
        self._next.clicked.connect(self._go_next)
        self._finish = QPushButton("Finish Lab")
        self._finish.setObjectName("Secondary")
        self._finish.clicked.connect(self._finish_lab)
        actions.addWidget(self._prev)
        actions.addWidget(self._submit)
        actions.addWidget(self._next)
        actions.addStretch()
        actions.addWidget(self._finish)
        left.addLayout(actions)

        self._feedback = QLabel("")
        self._feedback.setProperty("role", "muted")
        self._feedback.setWordWrap(True)
        self._feedback.setMinimumHeight(40)
        left.addWidget(self._feedback)

        left_widget = QWidget()
        left_widget.setLayout(left)
        root.addWidget(left_widget, 1)

        # Right: topology
        right = QVBoxLayout()
        right.setContentsMargins(16, 16, 24, 16)
        right.setSpacing(8)
        topo_label = QLabel("Topology")
        topo_label.setProperty("role", "h2")
        right.addWidget(topo_label)
        self._canvas = TopologyCanvas()
        right.addWidget(self._canvas, 1)
        right_widget = QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, 1)

    # -----/ Lifecycle /-----
    def start_lab(self, lab: LabBank) -> None:
        self._session = start_lab_session(lab)
        self._canvas.set_topology(lab.topology)
        self._render_current()

    def set_on_result(self, callback) -> None:
        self._on_result = callback

    def cleanup(self) -> None:
        pass

    # -----/ Rendering /-----
    def _render_current(self) -> None:
        if self._session is None:
            return
        sess = self._session
        task = sess.current_task
        self._task_header.setText(f"Task {sess.current_task_index + 1} / {len(sess.lab.tasks)}")
        self._instructions.setMarkdown(task.instructions.strip())
        # Restore previously submitted config for this task, if graded.
        grade = sess.grades.get(task.id)
        self._editor.setPlainText(grade.submitted_config if grade else "")
        self._feedback.setText("")
        self._prev.setEnabled(sess.current_task_index > 0)
        self._next.setEnabled(sess.current_task_index < len(sess.lab.tasks) - 1)

    def _go_prev(self) -> None:
        if self._session is None:
            return
        if self._session.previous_task() is not None:
            self._render_current()

    def _go_next(self) -> None:
        if self._session is None:
            return
        if self._session.next_task() is not None:
            self._render_current()

    def _submit_task(self) -> None:
        if self._session is None:
            return
        config = self._editor.toPlainText()
        grade = self._session.submit_task(config)
        self._feedback.setText(grade.feedback)
        # Advance to next task after submit (mirrors the HTTP router's
        # "Submit & Next" behavior), staying on the final task if applicable.
        if self._session.current_task_index < len(self._session.lab.tasks) - 1:
            self._session.next_task()
        self._render_current()

    def _finish_lab(self) -> None:
        if self._session is None:
            return
        result = finish_and_score_lab(self._session)
        if self._on_result:
            self._on_result(self._session, result)

    # -----/ Test hooks /-----
    def current_task_id(self) -> str | None:
        if self._session is None:
            return None
        return self._session.current_task.id

    def submit_config(self, config: str) -> None:
        if self._session is None:
            return
        self._editor.setPlainText(config)
        self._submit_task()
