"""NetSim in-process lab session — OpenIOS world + task grading."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from openboson.netsim.grader import TaskGrade, grade_task
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
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    @classmethod
    def create(cls, lab: LabBank) -> "LabSession":
        world = LabWorld.from_lab(lab)
        return cls(session_id=uuid.uuid4().hex, lab=lab, world=world)

    @property
    def current_task(self):
        return self.lab.tasks[self.current_task_index]

    def check_current_task(self) -> TaskGrade:
        """Grade the current task against live device running-configs."""
        task = self.current_task
        # Prefer device-scoped config if task mentions a device name.
        config = self._config_for_task(task.id, task.instructions)
        grade = grade_task(task, config)
        # Store the live combined config for review.
        grade.submitted_config = config
        self.grades[task.id] = grade
        return grade

    def check_all_tasks(self) -> dict[str, TaskGrade]:
        for i, task in enumerate(self.lab.tasks):
            self.current_task_index = i
            self.check_current_task()
        return self.grades

    def submit_task(self, config: str) -> TaskGrade:
        """Legacy API: grade current task against an explicit config blob.

        Still used by the HTTP router and older tests. Prefer
        ``check_current_task()`` for the GUI (grades live OpenIOS state).
        """
        task = self.current_task
        grade = grade_task(task, config)
        self.grades[task.id] = grade
        return grade

    def _config_for_task(self, task_id: str, instructions: str) -> str:
        """Pick the most relevant running-config text for grading."""
        text = (instructions or "").upper()
        # If instructions name a single device, grade that device first.
        named = [n for n in self.world.device_names() if n.upper() in text]
        if len(named) == 1:
            return self.world.devices[named[0]].running_config()
        # Otherwise combine all (grader looks for required lines anywhere).
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
        self.finished_at = datetime.now(timezone.utc)
        return self.finished_at


@dataclass
class LabResult:
    session_id: str
    lab_id: str
    lab_title: str
    total_tasks: int
    passed_tasks: int
    score: float  # 0.0 - 1.0
    task_grades: dict[str, TaskGrade] = field(default_factory=dict)

    @property
    def score_percent(self) -> float:
        return self.score * 100.0


def score_lab(session: LabSession) -> LabResult:
    """Compute a lab result from graded tasks."""
    total = len(session.lab.tasks)
    passed = sum(1 for g in session.grades.values() if g.is_correct)
    score = passed / total if total else 0.0
    return LabResult(
        session_id=session.session_id,
        lab_id=session.lab.lab_id,
        lab_title=session.lab.title,
        total_tasks=total,
        passed_tasks=passed,
        score=score,
        task_grades=dict(session.grades),
    )
