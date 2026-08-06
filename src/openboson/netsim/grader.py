"""Lab grading engine — per-device config comparison + verify blocks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from openboson.netsim.lab_schema import GradingRule, LabTask, VerifyBlock

if TYPE_CHECKING:
    from openboson.netsim.ios.world import LabWorld


@dataclass
class TaskGrade:
    """Result of grading one task's submitted config / live world state."""

    task_id: str
    is_correct: bool
    submitted_config: str = ""
    missing: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    order_violations: list[str] = field(default_factory=list)
    verify_failures: list[str] = field(default_factory=list)
    score: float = 0.0
    weight: float = 1.0
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
    if not missing:
        return ""
    cats: list[str] = []
    joined = " | ".join(missing).lower()

    def has(*needles: str) -> bool:
        return any(n in joined for n in needles)

    host_m = [m for m in missing if m.lower().startswith("hostname ")]
    for m in host_m:
        name = m.split(None, 1)[-1] if " " in m else "device"
        cats.append(f"Hostname on {name} is not set as required.")
    if has("ip address"):
        cats.append("Interface addressing is missing or incorrect.")
    if has("no shutdown"):
        cats.append("A required interface is still administratively down.")
    if has("vlan "):
        cats.append("Required VLAN definition is missing or incomplete.")
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
    if has("router ospf") or (has("network ") and has("area")):
        cats.append("Dynamic routing configuration is incomplete.")
    if (
        has("interface ")
        and not has("ip address")
        and not has("no shutdown")
        and not has("switchport")
    ):
        cats.append("A required interface section is missing from the configuration.")

    seen: set[str] = set()
    unique: list[str] = []
    for c in cats:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    if not unique:
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


def _grade_rules(
    rules: GradingRule, submitted_config: str
) -> tuple[list[str], list[str], list[str], float]:
    lines = _normalize_config(submitted_config)
    line_set = set(lines)
    missing = [r for r in rules.require if _normalize_line(r) not in line_set]
    forbidden_found = [f for f in rules.forbid if _normalize_line(f) in line_set]
    order_violations: list[str] = []
    if rules.require_order:
        positions: list[int] = []
        for cmd in rules.require_order:
            norm = _normalize_line(cmd)
            idx = next((i for i, line in enumerate(lines) if line == norm), None)
            positions.append(idx if idx is not None else -1)
        for i in range(len(positions) - 1):
            if positions[i] != -1 and positions[i + 1] != -1 and positions[i + 1] < positions[i]:
                order_violations.append("order")
    total_required = len(rules.require)
    satisfied = total_required - len(missing)
    score = (satisfied / total_required) if total_required else 1.0
    return missing, forbidden_found, order_violations, score


def evaluate_verify(verify: VerifyBlock, world: LabWorld) -> list[str]:
    """Return human-readable verify failures (never dumps solution commands)."""
    failures: list[str] = []
    for ping in verify.ping:
        try:
            result = world.ping(ping.source, ping.destination)
            ok = "100 percent" in result
        except Exception:
            ok = False
        if ok != ping.should_succeed:
            if ping.should_succeed:
                hint = ""
                try:
                    hint = world.explain_unreachable(ping.source, ping.destination)
                except Exception:
                    hint = ""
                msg = "Reachability check failed between required endpoints."
                if hint:
                    msg = f"{msg} {hint}"
                failures.append(msg)
            else:
                failures.append(
                    "Unexpected reachability between endpoints — "
                    "isolation or filtering is not in place yet."
                )
    for show in verify.show:
        device = world.devices.get(show.device)
        if device is None:
            failures.append("A required device is missing from the lab world.")
            continue
        text = device.running_config().lower()
        for needle in show.contains:
            if needle.lower() not in text:
                failures.append(
                    f"Show-state assertion failed on {show.device} — "
                    "required operational config is not present yet."
                )
                break
    return failures


def grade_task(
    task: LabTask,
    submitted_config: str | None,
    *,
    world: LabWorld | None = None,
) -> TaskGrade:
    """Grade a lab task against grading rules and optional live verify blocks."""
    weight = float(task.weight)
    if task.grading_rules is None and task.verify is None:
        return TaskGrade(
            task_id=task.id,
            is_correct=True,
            score=1.0,
            weight=weight,
            feedback="Objective met.",
        )

    missing: list[str] = []
    forbidden_found: list[str] = []
    order_violations: list[str] = []
    score = 1.0
    submitted = submitted_config or ""
    config = submitted

    if task.grading_rules is not None:
        rules = task.grading_rules
        # Honor an explicit submitted blob (legacy submit API / tests). Only fall
        # back to the live device running-config when nothing was submitted.
        if (
            not submitted.strip()
            and rules.device
            and world is not None
            and rules.device in world.devices
        ):
            config = world.devices[rules.device].running_config()
        else:
            config = submitted
        missing, forbidden_found, order_violations, score = _grade_rules(rules, config)
        weight = float(rules.weight if rules.weight is not None else task.weight)

    verify_failures: list[str] = []
    if task.verify is not None:
        if world is None:
            verify_failures.append("Live verification requires an active lab world.")
        else:
            verify_failures = evaluate_verify(task.verify, world)

    passed = not missing and not forbidden_found and not order_violations and not verify_failures
    if verify_failures:
        score = min(score, 0.0) if not passed and not missing else score * 0.5

    if passed:
        feedback = "Objective met."
    else:
        parts = [
            _coach_for_missing(missing),
            _coach_for_forbidden(forbidden_found),
            _coach_for_order(order_violations) if order_violations else "",
            " ".join(verify_failures),
        ]
        feedback = " ".join(p for p in parts if p).strip() or "Objective not met yet."

    return TaskGrade(
        task_id=task.id,
        is_correct=passed,
        submitted_config=config,
        missing=missing,
        forbidden_found=forbidden_found,
        order_violations=order_violations,
        verify_failures=verify_failures,
        score=score,
        weight=weight,
        feedback=feedback,
    )


def grade_lab(tasks: Iterable[LabTask], submitted_config: str) -> list[TaskGrade]:
    return [grade_task(t, submitted_config) for t in tasks]


def weighted_score(grades: dict[str, TaskGrade]) -> float:
    if not grades:
        return 0.0
    total_w = sum(max(g.weight, 0.0) for g in grades.values())
    if total_w <= 0:
        return 0.0
    earned = sum(max(g.weight, 0.0) * g.score for g in grades.values())
    return earned / total_w
