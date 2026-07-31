"""Tests for the NetSim config-comparison grader."""

from pathlib import Path

from openboson.netsim.grader import grade_task
from openboson.netsim.lab_loader import load_lab
from openboson.netsim.lab_schema import GradingRule, LabTask

DEMO_LAB_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_branch_office_access.yaml"
)


def _task(id_: str, require, forbid=None, require_order=None) -> LabTask:
    return LabTask(
        id=id_,
        instructions="x",
        grading_rules=GradingRule(
            require=list(require),
            forbid=list(forbid or []),
            require_order=list(require_order or []),
        ),
    )


def test_grade_task_correct():
    t = _task("t1", require=["hostname R1", "interface GigabitEthernet0/0", "no shutdown"])
    cfg = """
    hostname R1
    interface GigabitEthernet0/0
     ip address 10.0.0.1 255.255.255.0
     no shutdown
    """
    g = grade_task(t, cfg)
    assert g.is_correct is True
    assert g.missing == []
    assert g.score == 1.0
    assert "Objective met" in g.feedback


def test_grade_task_missing_coachy_no_commands():
    t = _task("t1", require=["hostname R1", "no shutdown"])
    g = grade_task(t, "hostname R1\ninterface G0/0\n")
    assert g.is_correct is False
    assert "no shutdown" in g.missing
    # Must not dump raw IOS into user feedback
    assert "no shutdown" not in g.feedback
    assert "Missing required" not in g.feedback
    assert g.feedback  # coachy text present


def test_grade_task_forbidden_command():
    t = _task("t1", require=["hostname R1"], forbid=["no ip domain-lookup"])
    g = grade_task(t, "hostname R1\nno ip domain-lookup\n")
    assert g.is_correct is False
    assert "no ip domain-lookup" in g.forbidden_found
    assert "no ip domain-lookup" not in g.feedback


def test_grade_task_ignores_comments_and_blanks():
    t = _task("t1", require=["hostname R1", "vlan 10"])
    cfg = """
    ! this is a comment
    hostname R1

    vlan 10
       name USERS
    """
    g = grade_task(t, cfg)
    assert g.is_correct is True


def test_grade_task_case_insensitive():
    t = _task("t1", require=["HOSTNAME R1"])
    g = grade_task(t, "hostname r1\n")
    assert g.is_correct is True


def test_grade_task_envelope_ignored():
    t = _task("t1", require=["hostname R1"])
    g = grade_task(t, "configure terminal\nhostname R1\nend\n")
    assert g.is_correct is True


def test_grade_task_require_order_ok():
    t = _task(
        "t1",
        require=["interface G0/0", "ip address 10.0.0.1 255.255.255.0"],
        require_order=["interface G0/0", "ip address 10.0.0.1 255.255.255.0"],
    )
    g = grade_task(t, "interface G0/0\n ip address 10.0.0.1 255.255.255.0\n")
    assert g.order_violations == []


def test_grade_task_require_order_violated():
    t = _task(
        "t1",
        require=["interface G0/0", "ip address 10.0.0.1 255.255.255.0"],
        require_order=["interface G0/0", "ip address 10.0.0.1 255.255.255.0"],
    )
    g = grade_task(t, "ip address 10.0.0.1 255.255.255.0\ninterface G0/0\n")
    assert g.order_violations


def test_grade_task_no_rules_is_pass():
    t = LabTask(id="t1", instructions="do it")
    g = grade_task(t, "anything")
    assert g.is_correct is True
    assert g.score == 1.0


def test_grade_demo_lab_t1_correct():
    lab = load_lab(DEMO_LAB_PATH)
    t1 = next(t for t in lab.tasks if t.id == "t1")
    g = grade_task(t1, t1.expected_config or "")
    assert g.is_correct is True


def test_grade_demo_lab_t2_partial():
    lab = load_lab(DEMO_LAB_PATH)
    t2 = next(t for t in lab.tasks if t.id == "t2")
    g = grade_task(t2, "hostname SW1\n")
    assert g.is_correct is False
    assert "vlan 10" in g.missing
    assert "switchport mode trunk" not in g.feedback
