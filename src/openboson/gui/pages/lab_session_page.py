"""NetSim lab session — OpenIOS multi-device consoles + topology + tasks."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QToolButton,
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
        self._tab_devices: list[str] = []
        self._tabs_connected = False
        self._split: QSplitter | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(10, 6, 10, 4)
        self._title = QLabel("Lab")
        self._title.setProperty("role", "h2")
        top.addWidget(self._title)
        top.addStretch()
        self._task_badge = QLabel("")
        self._task_badge.setProperty("role", "muted")
        top.addWidget(self._task_badge)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        self._split = split

        # LEFT: objectives (side pane chrome)
        left = QWidget()
        left.setObjectName("LabSidePane")
        left.setMinimumWidth(0)
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(10, 6, 6, 10)
        left_l.setSpacing(6)

        tasks_hdr = QLabel("Objectives")
        tasks_hdr.setProperty("role", "h2")
        left_l.addWidget(tasks_hdr)

        self._task_list = QVBoxLayout()
        self._task_list.setSpacing(4)
        left_l.addLayout(self._task_list)

        inst_hdr = QLabel("Current objective")
        inst_hdr.setProperty("role", "muted")
        left_l.addWidget(inst_hdr)
        self._instructions = QTextBrowser()
        self._instructions.setOpenExternalLinks(False)
        self._instructions.setFrameShape(QFrame.Shape.NoFrame)
        self._instructions.setMinimumHeight(100)
        left_l.addWidget(self._instructions, 1)

        self._feedback = QLabel("")
        self._feedback.setWordWrap(True)
        self._feedback.setProperty("role", "muted")
        self._feedback.setMinimumHeight(40)
        left_l.addWidget(self._feedback)

        nav = QHBoxLayout()
        self._prev = QPushButton("‹ Prev")
        self._prev.setObjectName("Secondary")
        self._prev.clicked.connect(self._go_prev)
        self._check = QPushButton("Check Task")
        self._check.setObjectName("Primary")
        self._check.clicked.connect(self._check_task)
        self._next = QPushButton("Next ›")
        self._next.setObjectName("Secondary")
        self._next.clicked.connect(self._go_next)
        nav.addWidget(self._prev)
        nav.addWidget(self._check)
        nav.addWidget(self._next)
        left_l.addLayout(nav)

        secondary = QHBoxLayout()
        self._finish = QPushButton("Finish Lab")
        self._finish.setObjectName("Secondary")
        self._finish.clicked.connect(self._finish_lab)
        self._lab_menu_btn = QToolButton()
        self._lab_menu_btn.setText("Lab actions")
        self._lab_menu_btn.setObjectName("Secondary")
        self._lab_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self._lab_menu_btn)
        menu.addAction("Reset Lab", self._reset_lab)
        menu.addAction("Reset & Replay", self._reset_and_replay)
        self._lab_menu_btn.setMenu(menu)
        secondary.addWidget(self._lab_menu_btn)
        secondary.addStretch()
        secondary.addWidget(self._finish)
        left_l.addLayout(secondary)
        split.addWidget(left)

        # CENTER: consoles (IDE focus — larger stretch)
        center = QWidget()
        center.setMinimumWidth(0)
        cl = QVBoxLayout(center)
        cl.setContentsMargins(4, 6, 4, 10)
        cl.setSpacing(4)
        cons_row = QHBoxLayout()
        cons_hdr = QLabel("Console")
        cons_hdr.setProperty("role", "h2")
        cons_row.addWidget(cons_hdr)
        cons_row.addStretch()
        self._console_device = QLabel("")
        self._console_device.setProperty("role", "muted")
        cons_row.addWidget(self._console_device)
        cl.addLayout(cons_row)
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        cl.addWidget(self._tabs, 1)
        split.addWidget(center)

        # RIGHT: topology
        right = QWidget()
        right.setObjectName("LabSidePane")
        right.setMinimumWidth(0)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 6, 10, 10)
        rl.setSpacing(4)
        topo_hdr = QLabel("Topology")
        topo_hdr.setProperty("role", "h2")
        rl.addWidget(topo_hdr)
        self._canvas = TopologyCanvas()
        self._canvas.deviceSelected.connect(self._on_device_clicked)
        rl.addWidget(self._canvas, 1)
        split.addWidget(right)

        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 6)
        split.setStretchFactor(2, 3)
        for i in range(3):
            split.setCollapsible(i, True)
        split.setSizes([220, 580, 300])
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
        self._tab_devices.clear()
        self._session = None

    def _build_terminals(self) -> None:
        if self._tabs_connected:
            self._tabs.currentChanged.disconnect(self._on_tab_changed)
            self._tabs_connected = False
        self._tabs.clear()
        self._terminals.clear()
        self._tab_devices.clear()
        if self._session is None:
            return
        world = self._session.world
        for name in world.device_names():
            term = CiscoTerminal(world.shell(name))
            self._terminals[name] = term
            self._tab_devices.append(name)
            role = world.devices[name].role.value
            self._tabs.addTab(term, f"  {name}  ·  {role}  ")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs_connected = True

    def _on_tab_changed(self, idx: int) -> None:
        if idx < 0 or self._session is None or idx >= len(self._tab_devices):
            return
        name = self._tab_devices[idx]
        self._console_device.setText(name)
        self._canvas.set_selected(name)
        term = self._terminals.get(name)
        if term is not None:
            term.setFocus()
        self._sync_topology_status()

    def _on_device_clicked(self, name: str) -> None:
        self._select_device(name)

    def _select_device(self, name: str) -> None:
        if name in self._tab_devices:
            self._tabs.setCurrentIndex(self._tab_devices.index(name))
        self._canvas.set_selected(name)
        self._console_device.setText(name)
        term = self._terminals.get(name)
        if term is not None:
            term.setFocus()

    def _sync_topology_status(self) -> None:
        if self._session is None:
            return
        world = self._session.world
        self._canvas.set_link_states(world.link_states())
        for name, dev in world.devices.items():
            ip = next((i.ip for i in dev.interfaces.values() if i.ip), None)
            label = f"{dev.hostname} · {ip}" if ip else dev.hostname
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
                mark, obj = "○", "LabObjectivePending"
            elif grade.is_correct:
                mark, obj = "✓", "LabObjectivePassed"
            else:
                mark, obj = "✗", "LabObjectiveFailed"
            btn = QPushButton(f"{mark}  Objective {i + 1}")
            btn.setObjectName(obj)
            btn.clicked.connect(lambda _=False, idx=i: self._goto_task(idx))
            self._task_list.addWidget(btn)

    def _set_feedback(self, text: str, *, ok: bool | None = None) -> None:
        self._feedback.setText(text)
        if ok is True:
            self._feedback.setObjectName("LabFeedbackOk")
        elif ok is False:
            self._feedback.setObjectName("LabFeedbackBad")
        else:
            self._feedback.setObjectName("")
            self._feedback.setProperty("role", "muted")
        self._feedback.style().unpolish(self._feedback)
        self._feedback.style().polish(self._feedback)

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
            self._set_feedback("")
        else:
            self._set_feedback(grade.feedback, ok=grade.is_correct)
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
        self._set_feedback(grade.feedback, ok=grade.is_correct)
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
            "Reset topology and task progress?\n\n"
            "This clears grades and restores base configs.\n"
            "Use Lab actions → Reset & Replay to rebuild and replay typed commands.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._do_reset(replay=False)

    def _reset_and_replay(self) -> None:
        if self._session is None:
            return
        from PySide6.QtWidgets import QMessageBox

        if not self._session.command_log:
            QMessageBox.information(self, "Nothing to replay", "No commands recorded yet.")
            return
        confirm = QMessageBox.question(
            self,
            "Reset & Replay?",
            f"Rebuild the lab and replay {len(self._session.command_log)} command(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._do_reset(replay=True)

    def _do_reset(self, *, replay: bool) -> None:
        if self._session is None:
            return
        self._session.reset(replay=replay)
        self._build_terminals()
        self._render_tasks()
        self._render_current()
        msg = "Lab reset and commands replayed." if replay else "Lab reset."
        self._set_feedback(msg)
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
        # Refresh bound terminal display if present.
        term = self._terminals.get(device)
        if term is not None:
            term.bind_shell(sh)
        self._sync_topology_status()

    def submit_config(self, config: str) -> None:
        self._check_task()
