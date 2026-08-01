"""NetSim in-process lab session — OpenIOS world + task grading."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from openboson.netsim.grader import TaskGrade, grade_task, weighted_score
from openboson.netsim.ios.device import DeviceRole
from openboson.netsim.ios.world import LabWorld
from openboson.netsim.lab_schema import LabBank


@dataclass
class LabSession:
    """A single run of a guided lab backed by a live OpenIOS LabWorld."""

    session_id: str
    lab: LabBank
    world: LabWorld
    current_task_index: int = 0
    grades: dict[str, TaskGrade] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    command_log: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def create(cls, lab: LabBank) -> LabSession:
        world = LabWorld.from_lab(lab)
        session = cls(session_id=uuid.uuid4().hex, lab=lab, world=world)
        session._wire_command_logging()
        session._apply_base_configs()
        return session

    def _wire_command_logging(self) -> None:
        """Wrap each shell ``feed`` so student commands are recorded for replay."""
        for name in self.world.device_names():
            shell = self.world.shell(name)
            original = shell.feed

            def make_feed(dev: str = name, orig=original):
                def feed(line: str) -> str:
                    text = (line or "").rstrip("\n")
                    if text.strip() and not text.strip().startswith("!"):
                        self.command_log.append((dev, text))
                    return orig(line)

                return feed

            shell.feed = make_feed()  # type: ignore[method-assign]

    def _apply_base_configs(self) -> None:
        """Feed each device's optional base_config through its shell."""
        # Base configs are bootstrap, not student commands — pause logging.
        saved = list(self.command_log)
        for device in self.lab.topology.devices:
            if not device.base_config:
                continue
            shell = self.world.shell(device.name)
            runtime = self.world.devices[device.name]
            lines = [
                raw.strip()
                for raw in device.base_config.splitlines()
                if raw.strip() and not raw.strip().startswith("!")
            ]
            if not lines:
                continue
            if runtime.role == DeviceRole.PC:
                for line in lines:
                    shell.feed(line)
            else:
                # OpenIOS requires privileged config mode for interface/routing lines.
                shell.feed("enable")
                shell.feed("configure terminal")
                for line in lines:
                    shell.feed(line)
                shell.feed("end")
        self.command_log[:] = saved

    def reset(self, *, replay: bool = False) -> None:
        """Restore topology, base configs, and task index; clear grades.

        When ``replay`` is True, re-feed the prior student ``command_log`` after
        rebuilding the world (lab walkthrough replay).
        """
        log = list(self.command_log) if replay else []
        self.world = LabWorld.from_lab(self.lab)
        self.command_log.clear()
        self._wire_command_logging()
        self._apply_base_configs()
        self.current_task_index = 0
        self.grades.clear()
        self.finished_at = None
        if replay and log:
            for device, line in log:
                if device not in self.world.devices:
                    continue
                self.world.shell(device).feed(line)

    @property
    def current_task(self):
        return self.lab.tasks[self.current_task_index]

    def check_current_task(self) -> TaskGrade:
        """Grade the current task against live device running-configs."""
        task = self.current_task
        config = self._config_for_task(task)
        grade = grade_task(task, config, world=self.world)
        grade.submitted_config = config
        self.grades[task.id] = grade
        return grade

    def check_all_tasks(self) -> dict[str, TaskGrade]:
        for i, _task in enumerate(self.lab.tasks):
            self.current_task_index = i
            self.check_current_task()
        return self.grades

    def submit_task(self, config: str) -> TaskGrade:
        """Legacy API: grade current task against an explicit config blob."""
        task = self.current_task
        grade = grade_task(task, config, world=self.world)
        self.grades[task.id] = grade
        return grade

    def _config_for_task(self, task) -> str:
        rules = task.grading_rules
        if rules and rules.device and rules.device in self.world.devices:
            return self.world.devices[rules.device].running_config()
        text = (task.instructions or "").upper()
        named = [n for n in self.world.device_names() if n.upper() in text]
        if len(named) == 1:
            return self.world.devices[named[0]].running_config()
        return self.world.combined_running_config()

    def next_task(self):
        if self.current_task_index < len(self.lab.tasks) - 1:
            self.current_task_index += 1
            return self.current_task
        return None

    def previous_task(self):
        if self.current_task_index > 0:
            self.current_task_index -= 1
            return self.current_task
        return None

    def goto(self, index: int):
        if 0 <= index < len(self.lab.tasks):
            self.current_task_index = index
            return self.current_task
        raise IndexError(index)

    def is_finished(self) -> bool:
        return self.finished_at is not None

    def finish(self) -> datetime:
        self.finished_at = datetime.now(UTC)
        return self.finished_at


@dataclass
class LabResult:
    session_id: str
    lab_id: str
    lab_title: str
    total_tasks: int
    passed_tasks: int
    score: float
    passed: bool = False
    task_grades: dict[str, TaskGrade] = field(default_factory=dict)

    @property
    def score_percent(self) -> float:
        return self.score * 100.0


def score_lab(session: LabSession) -> LabResult:
    """Compute a lab result using weighted task scores and pass_threshold."""
    total = len(session.lab.tasks)
    # Score only graded tasks; ungraded tasks count as zero weight earned.
    grades = dict(session.grades)
    for task in session.lab.tasks:
        if task.id not in grades:
            grades[task.id] = TaskGrade(
                task_id=task.id,
                is_correct=False,
                score=0.0,
                weight=float(task.weight),
                feedback="Not graded.",
            )
    passed_tasks = sum(1 for g in grades.values() if g.is_correct)
    score = weighted_score(grades)
    threshold = float(getattr(session.lab, "pass_threshold", 1.0) or 1.0)
    return LabResult(
        session_id=session.session_id,
        lab_id=session.lab.lab_id,
        lab_title=session.lab.title,
        total_tasks=total,
        passed_tasks=passed_tasks,
        score=score,
        passed=score >= threshold,
        task_grades=grades,
    )
