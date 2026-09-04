"""Live-grade STP gold lab: PC ping fails until PortFast on both access ports."""

from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab

LAB = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_stp_portfast_edge.yaml"


def _feed(session: LabSession, device: str, *lines: str) -> None:
    shell = session.world.shell(device)
    for line in lines:
        shell.feed(line)


def test_stp_lab_fails_after_vlan_access_and_passes_after_portfast():
    lab = load_lab(LAB)
    sess = LabSession.create(lab)
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "STP gold lab must prove PC1→PC2 with verify.ping"
    assert all(
        p.source == "PC1" and p.destination == "10.10.10.20"
        for t in ping_tasks
        for p in t.verify.ping
    )

    _feed(
        sess,
        "SW1",
        "enable",
        "configure terminal",
        "vlan 10",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport mode access",
        "switchport access vlan 10",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 10",
        "end",
    )
    grades = sess.check_all_tasks()
    assert any(not grades[t.id].is_correct for t in ping_tasks)
    assert "Success rate is 0 percent" in sess.world.ping("PC1", "10.10.10.20")

    _feed(
        sess,
        "SW1",
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/1",
        "spanning-tree portfast",
        "interface GigabitEthernet0/2",
        "spanning-tree portfast",
        "end",
    )
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0
