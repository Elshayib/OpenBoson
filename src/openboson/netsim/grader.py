"""Lab grading engine — Phase 1: configuration comparison.

The grader compares a user's submitted device configuration text against a
task's ``GradingRule``. It is intentionally simple and deterministic: it
normalizes IOS-like config lines and checks ``require`` / ``forbid`` /
``require_order`` rules.

Normalization:
    - Lowercase for matching, but keep original for feedback.
    - Strip surrounding whitespace and collapse internal whitespace.
    - Drop blank lines and ``!``/``#`` comment lines.
    - Ignore the ``configure terminal`` / ``end`` envelope lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from openboson.netsim.lab_schema import GradingRule, LabTask


@dataclass
class TaskGrade:
    """Result of grading one task's submitted config."""

    task_id: str
    is_correct: bool
    missing: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    order_violations: list[str] = field(default_factory=list)
    score: float = 0.0  # 0.0 - 1.0 (fraction of require rules satisfied)
    feedback: str = ""

    @property
    def passed(self) -> bool:
        return self.is_correct


def _normalize_line(line: str) -> str:
    s = " ".join(line.strip().split())
    return s.lower()


def _normalize_config(config: str) -> list[str]:
    """Return normalized, non-empty config lines (lowercased)."""
    out: list[str] = []
    for raw in config.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("!"):
            continue
        if s.startswith("#"):
            continue
        # Drop the config envelope.
        if s in ("configure terminal", "conf t", "end", "exit"):
            continue
        out.append(_normalize_line(raw))
    return out


def grade_task(task: LabTask, submitted_config: str) -> TaskGrade:
    """Grade a single lab task's submitted config against its grading rules."""
    if task.grading_rules is None:
        # No rules -> nothing to grade; treat as a manual/visual step (pass).
        return TaskGrade(
            task_id=task.id,
            is_correct=True,
            score=1.0,
            feedback="No automated grading rules for this task.",
        )

    rules = task.grading_rules
    lines = _normalize_config(submitted_config)
    line_set = set(lines)

    # require
    missing = [r for r in rules.require if _normalize_line(r) not in line_set]
    # forbid
    forbidden_found = [f for f in rules.forbid if _normalize_line(f) in line_set]
    # require_order
    order_violations: list[str] = []
    if rules.require_order:
        # Find positions of each ordered command; check monotonic increasing.
        positions: list[int] = []
        for cmd in rules.require_order:
            norm = _normalize_line(cmd)
            idx = next((i for i, l in enumerate(lines) if l == norm), None)
            positions.append(idx if idx is not None else -1)
        # Report any adjacent pair that appears out of order.
        for i in range(len(positions) - 1):
            if positions[i] != -1 and positions[i + 1] != -1 and positions[i + 1] < positions[i]:
                order_violations.append(
                    f"{rules.require_order[i]} must precede {rules.require_order[i + 1]}"
                )

    total_required = len(rules.require)
    satisfied = total_required - len(missing)
    score = (satisfied / total_required) if total_required else 1.0

    passed = not missing and not forbidden_found and not order_violations
    feedback_parts: list[str] = []
    if missing:
        feedback_parts.append("Missing required commands: " + "; ".join(missing))
    if forbidden_found:
        feedback_parts.append("Found forbidden commands: " + "; ".join(forbidden_found))
    if order_violations:
        feedback_parts.append("Ordering issue: " + "; ".join(order_violations))
    if not feedback_parts:
        feedback_parts.append("All requirements met.")

    return TaskGrade(
        task_id=task.id,
        is_correct=passed,
        missing=missing,
        forbidden_found=forbidden_found,
        order_violations=order_violations,
        score=score,
        feedback=" ".join(feedback_parts),
    )


def grade_lab(tasks: Iterable[LabTask], submitted_config: str) -> list[TaskGrade]:
    """Grade all tasks against one submitted config blob.

    NOTE: For MVP the user submits a single concatenated config (the grader
    treats all tasks as one document). Per-task grading that splits config by
    device arrives in a later iteration.
    """
    return [grade_task(t, submitted_config) for t in tasks]
