"""Lab grading engine — config comparison + coachy high-level feedback."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from openboson.netsim.lab_schema import GradingRule, LabTask


@dataclass
class TaskGrade:
    """Result of grading one task's submitted config."""

    task_id: str
    is_correct: bool
    submitted_config: str = ""
    missing: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    order_violations: list[str] = field(default_factory=list)
    score: float = 0.0  # 0.0 - 1.0
    feedback: str = ""

    @property
    def passed(self) -> bool:
        return self.is_correct


def _normalize_line(line: str) -> str:
    return " ".join(line.strip().split()).lower()


def _normalize_config(config: str) -> list[str]:
    out: list[str] = []
    for raw in config.splitlines():
        s = raw.strip()
        if not s or s.startswith("!") or s.startswith("#"):
            continue
        if s.lower() in {"configure terminal", "conf t", "end", "exit"}:
            continue
        out.append(_normalize_line(raw))
    return out


def _coach_for_missing(missing: list[str]) -> str:
    """Map missing config lines → coachy high-level feedback (no IOS commands)."""
    if not missing:
        return ""

    cats: list[str] = []
    joined = " | ".join(missing).lower()

    def has(*needles: str) -> bool:
        return any(n in joined for n in needles)

    # Hostname
    host_m = [m for m in missing if m.lower().startswith("hostname ")]
    for m in host_m:
        name = m.split(None, 1)[-1] if " " in m else "device"
        cats.append(f"Hostname on {name} is not set as required.")

    # Addressing
    if has("ip address"):
        # Try extract device context from surrounding missing interface lines
        cats.append("Interface addressing is missing or incorrect.")

    if has("no shutdown"):
        cats.append("A required interface is still administratively down.")

    if has("vlan "):
        cats.append("Required VLAN definition is missing or incomplete.")

    if has("name ") and has("vlan"):
        pass  # covered
    elif any(m.lower().startswith("name ") for m in missing):
        cats.append("VLAN naming is incomplete.")

    if has("switchport mode trunk"):
        cats.append("Uplink trunking is not configured correctly.")

    if has("switchport mode access") or has("switchport access vlan"):
        cats.append("Access-port VLAN assignment is incomplete.")

    if has("ip route") or has("ip default-gateway"):
        cats.append("Required routing or default gateway is missing.")

    if has("access-list") or has("ip access-group"):
        cats.append("Access control configuration is incomplete.")

    if has("ip nat") or has("nat "):
        cats.append("NAT configuration is incomplete.")

    if has("ip dhcp") or has("dhcp "):
        cats.append("DHCP service configuration is incomplete.")

    if has("router ospf") or has("network ") and has("area"):
        cats.append("Dynamic routing configuration is incomplete.")

    if has("interface "):
        # only if not already covered by ip/no shut
        if not has("ip address") and not has("no shutdown") and not has("switchport"):
            cats.append("A required interface section is missing from the configuration.")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in cats:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    if not unique:
        # Generic — still no command dump
        n = len(missing)
        unique.append(
            f"{n} required configuration item{'s' if n != 1 else ''} "
            f"{'are' if n != 1 else 'is'} still missing or incorrect."
        )
    return " ".join(unique)


def _coach_for_forbidden(forbidden: list[str]) -> str:
    if not forbidden:
        return ""
    joined = " ".join(forbidden).lower()
    if "switchport mode access" in joined:
        return "An interface that should be a trunk still looks like an access port."
    if "shutdown" in joined:
        return "A required interface appears to be shut down."
    return "Configuration contains settings that conflict with the objective."


def _coach_for_order(_violations: list[str]) -> str:
    return "Some configuration appears out of the expected logical order."


def grade_task(task: LabTask, submitted_config: str) -> TaskGrade:
    """Grade a single lab task's submitted config against its grading rules."""
    if task.grading_rules is None:
        return TaskGrade(
            task_id=task.id,
            is_correct=True,
            score=1.0,
            feedback="Objective met.",
        )

    rules = task.grading_rules
    lines = _normalize_config(submitted_config)
    line_set = set(lines)

    missing = [r for r in rules.require if _normalize_line(r) not in line_set]
    forbidden_found = [f for f in rules.forbid if _normalize_line(f) in line_set]
    order_violations: list[str] = []
    if rules.require_order:
        positions: list[int] = []
        for cmd in rules.require_order:
            norm = _normalize_line(cmd)
            idx = next((i for i, l in enumerate(lines) if l == norm), None)
            positions.append(idx if idx is not None else -1)
        for i in range(len(positions) - 1):
            if positions[i] != -1 and positions[i + 1] != -1 and positions[i + 1] < positions[i]:
                order_violations.append("order")

    total_required = len(rules.require)
    satisfied = total_required - len(missing)
    score = (satisfied / total_required) if total_required else 1.0
    passed = not missing and not forbidden_found and not order_violations

    if passed:
        feedback = "Objective met."
    else:
        parts = [
            _coach_for_missing(missing),
            _coach_for_forbidden(forbidden_found),
            _coach_for_order(order_violations) if order_violations else "",
        ]
        feedback = " ".join(p for p in parts if p).strip() or "Objective not met yet."

    return TaskGrade(
        task_id=task.id,
        is_correct=passed,
        submitted_config=submitted_config,
        missing=missing,
        forbidden_found=forbidden_found,
        order_violations=order_violations,
        score=score,
        feedback=feedback,
    )


def grade_lab(tasks: Iterable[LabTask], submitted_config: str) -> list[TaskGrade]:
    return [grade_task(t, submitted_config) for t in tasks]
