"""NetSim lab session — OpenIOS multi-device consoles + topology + tasks."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from openboson.gui.engine import finish_and_score_lab, start_lab_session
from openboson.gui.widgets.cisco_terminal import CiscoTerminal
from openboson.gui.widgets.topology_canvas import TopologyCanvas
from openboson.netsim.lab_schema import LabBank
from openboson.netsim.session import LabSession


class LabSessionPage(QWidget):
    """Guided lab with real per-device CLI and interactive topology."""

    title = "Lab"

    def __init__(self) -> None:
        super().__init__()
        self._session: LabSession | None = None
        self._on_result = None
        self._terminals: dict[str, CiscoTerminal] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 8)
        self._title = QLabel("Lab")
        self._title.setProperty("role", "h2")
        top.addWidget(self._title)
        top.addStretch()
        self._task_badge = QLabel("")
        self._task_badge.setProperty("role", "muted")
        top.addWidget(self._task_badge)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: objectives
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(16, 8, 8, 16)
        left_l.setSpacing(10)

        tasks_hdr = QLabel("Objectives")
        tasks_hdr.setProperty("role", "h2")
        left_l.addWidget(tasks_hdr)

        self._task_list = QVBoxLayout()
        self._task_list.setSpacing(6)
        left_l.addLayout(self._task_list)

        inst_hdr = QLabel("Current objective")
        inst_hdr.setProperty("role", "muted")
        left_l.addWidget(inst_hdr)
        self._instructions = QTextBrowser()
        self._instructions.setOpenExternalLinks(False)
        self._instructions.setFrameShape(QFrame.Shape.NoFrame)
        self._instructions.setMinimumHeight(120)
        left_l.addWidget(self._instructions, 1)

        self._feedback = QLabel("")
        self._feedback.setWordWrap(True)
        self._feedback.setProperty("role", "muted")
        self._feedback.setMinimumHeight(48)
        left_l.addWidget(self._feedback)

        actions = QHBoxLayout()
        self._check = QPushButton("Check Task")
        self._check.setObjectName("Primary")
        self._check.clicked.connect(self._check_task)
        self._prev = QPushButton("‹ Prev")
        self._prev.setObjectName("Secondary")
        self._prev.clicked.connect(self._go_prev)
        self._next = QPushButton("Next ›")
        self._next.setObjectName("Secondary")
        self._next.clicked.connect(self._go_next)
        self._finish = QPushButton("Finish Lab")
        self._finish.setObjectName("Secondary")
        self._finish.clicked.connect(self._finish_lab)
        self._reset = QPushButton("Reset Lab")
        self._reset.setObjectName("Secondary")
        self._reset.clicked.connect(self._reset_lab)
        actions.addWidget(self._prev)
        actions.addWidget(self._check)
        actions.addWidget(self._next)
        actions.addStretch()
        actions.addWidget(self._reset)
        actions.addWidget(self._finish)
        left_l.addLayout(actions)
        split.addWidget(left)

        # CENTER: consoles
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(8, 8, 8, 16)
        cl.setSpacing(6)
        cons_hdr = QLabel("Console")
        cons_hdr.setProperty("role", "h2")
        cl.addWidget(cons_hdr)
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        cl.addWidget(self._tabs, 1)
        split.addWidget(center)

        # RIGHT: topology
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 8, 16, 16)
        rl.setSpacing(6)
        topo_hdr = QLabel("Topology")
        topo_hdr.setProperty("role", "h2")
        rl.addWidget(topo_hdr)
        self._canvas = TopologyCanvas()
        self._canvas.deviceSelected.connect(self._on_device_clicked)
        rl.addWidget(self._canvas, 1)
        split.addWidget(right)

        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 4)
        split.setStretchFactor(2, 3)
        root.addWidget(split, 1)

    def start_lab(self, lab: LabBank) -> None:
        self._session = start_lab_session(lab)
        self._title.setText(lab.title)
        self._canvas.set_topology(lab.topology)
        self._build_terminals()
        self._render_tasks()
        self._render_current()
        names = self._session.world.device_names()
        if names:
            self._select_device(names[0])

    def set_on_result(self, callback) -> None:
        self._on_result = callback

    def is_lab_active(self) -> bool:
        return self._session is not None

    def cleanup(self) -> None:
        self._terminals.clear()
        self._session = None

    def _build_terminals(self) -> None:
        self._tabs.clear()
        self._terminals.clear()
        if self._session is None:
            return
        world = self._session.world
        for name in world.device_names():
            term = CiscoTerminal(world.shell(name))
            # Subtle role tint on tab via stylesheet is limited; label carries role.
            self._terminals[name] = term
            role = world.devices[name].role.value
            self._tabs.addTab(term, f"  {name}  ·  {role}  ")
        self._tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx: int) -> None:
        if idx < 0 or self._session is None:
            return
        name = self._tabs.tabText(idx).strip().split()[0]
        self._canvas.set_selected(name)
        self._sync_topology_status()

    def _on_device_clicked(self, name: str) -> None:
        self._select_device(name)

    def _select_device(self, name: str) -> None:
        for i in range(self._tabs.count()):
            if self._tabs.tabText(i).strip().startswith(name):
                self._tabs.setCurrentIndex(i)
                break
        self._canvas.set_selected(name)

    def _sync_topology_status(self) -> None:
        if self._session is None:
            return
        world = self._session.world
        self._canvas.set_link_states(world.link_states())
        for name, dev in world.devices.items():
            sum(1 for i in dev.interfaces.values() if i.admin_up and i.protocol_up)
            ip = next((i.ip for i in dev.interfaces.values() if i.ip), None)
            label = dev.hostname
            if ip:
                label = f"{dev.hostname} · {ip}"
            self._canvas.set_device_status(name, label)
            self._canvas.set_device_tooltip(name, world.device_tooltip(name))

    def _render_tasks(self) -> None:
        while self._task_list.count():
            item = self._task_list.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if self._session is None:
            return
        for i, task in enumerate(self._session.lab.tasks):
            grade = self._session.grades.get(task.id)
            if grade is None:
                mark, color = "○", "#8b9cb3"
            elif grade.is_correct:
                mark, color = "✓", "#3fb950"
            else:
                mark, color = "✗", "#f85149"
            btn = QPushButton(f"{mark}  Objective {i + 1}")
            btn.setStyleSheet(f"text-align: left; color: {color};")
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _=False, idx=i: self._goto_task(idx))
            self._task_list.addWidget(btn)

    def _render_current(self) -> None:
        if self._session is None:
            return
        sess = self._session
        task = sess.current_task
        n = len(sess.lab.tasks)
        self._task_badge.setText(f"Objective {sess.current_task_index + 1} / {n}")
        self._instructions.setMarkdown(task.instructions.strip())
        grade = sess.grades.get(task.id)
        if grade is None:
            self._feedback.setText("")
            self._feedback.setStyleSheet("")
        else:
            self._feedback.setText(grade.feedback)
            self._feedback.setStyleSheet(
                "color: #3fb950;" if grade.is_correct else "color: #f85149;"
            )
        self._prev.setEnabled(sess.current_task_index > 0)
        self._next.setEnabled(sess.current_task_index < n - 1)
        self._render_tasks()
        self._sync_topology_status()

    def _goto_task(self, idx: int) -> None:
        if self._session is None:
            return
        self._session.goto(idx)
        self._render_current()

    def _go_prev(self) -> None:
        if self._session and self._session.previous_task() is not None:
            self._render_current()

    def _go_next(self) -> None:
        if self._session and self._session.next_task() is not None:
            self._render_current()

    def _check_task(self) -> None:
        if self._session is None:
            return
        grade = self._session.check_current_task()
        self._feedback.setText(grade.feedback)
        self._feedback.setStyleSheet("color: #3fb950;" if grade.is_correct else "color: #f85149;")
        self._render_tasks()
        self._sync_topology_status()

    def _finish_lab(self) -> None:
        if self._session is None:
            return
        self._session.check_all_tasks()
        result = finish_and_score_lab(self._session)
        if self._on_result:
            self._on_result(self._session, result)

    def _reset_lab(self) -> None:
        if self._session is None:
            return
        from PySide6.QtWidgets import QMessageBox

        confirm = QMessageBox.question(
            self,
            "Reset lab?",
            "Reset topology, base configurations, and task progress?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._session.reset()
        self._build_terminals()
        self._render_tasks()
        self._render_current()
        self._feedback.setText("Lab reset.")
        self._feedback.setStyleSheet("")
        names = self._session.world.device_names()
        if names:
            self._select_device(names[0])
        self._sync_topology_status()

    def current_task_id(self) -> str | None:
        if self._session is None:
            return None
        return self._session.current_task.id

    def type_on_device(self, device: str, *lines: str) -> None:
        if self._session is None:
            return
        sh = self._session.world.shell(device)
        for line in lines:
            sh.feed(line)
        self._sync_topology_status()

    def submit_config(self, config: str) -> None:
        self._check_task()
