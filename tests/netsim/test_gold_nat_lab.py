"""Live-grade NAT gold lab: PC→ISP ping fails until PAT overload."""

from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab

LAB = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_nat_pat_edge.yaml"


def test_nat_lab_fails_before_pat_and_passes_after():
    lab = load_lab(LAB)
    sess = LabSession.create(lab)
    # Base addressing only — no PAT
    grades = sess.check_all_tasks()
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "NAT gold lab must prove PC→ISP with verify.ping"
    assert any(not grades[t.id].is_correct for t in ping_tasks)
    assert all(
        p.source == "PC1" and p.destination == "203.0.113.2"
        for t in ping_tasks
        for p in t.verify.ping
    )

    r1 = sess.world.shell("R1")
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip nat inside",
        "interface GigabitEthernet0/1",
        "ip nat outside",
        "exit",
        "access-list 1 permit any",
        "ip nat inside source list 1 interface GigabitEthernet0/1 overload",
        "end",
    ):
        r1.feed(line)
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0
