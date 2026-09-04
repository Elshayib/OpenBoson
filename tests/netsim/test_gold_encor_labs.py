"""Live-grade ENCOR gold labs that depend on NAT or DHCP verify."""

from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab

ROOT = Path(__file__).resolve().parents[2] / "data" / "demo_labs"
PAT = ROOT / "encor_pat_edge.yaml"
DHCP = ROOT / "encor_dhcp_campus.yaml"


def _feed(session: LabSession, device: str, *lines: str) -> None:
    shell = session.world.shell(device)
    for line in lines:
        shell.feed(line)


def test_encor_pat_lab_fails_before_pat_and_passes_after():
    lab = load_lab(PAT)
    sess = LabSession.create(lab)
    grades = sess.check_all_tasks()
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "ENCOR PAT gold lab must prove PC→outside with verify.ping"
    assert any(not grades[t.id].is_correct for t in ping_tasks)
    assert all(
        p.source == "PC1" and p.destination == "198.51.100.2"
        for t in ping_tasks
        for p in t.verify.ping
    )

    _feed(
        sess,
        "R1",
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
    )
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0


def test_encor_dhcp_lab_fails_before_renew_and_passes_after():
    lab = load_lab(DHCP)
    sess = LabSession.create(lab)
    assert sess.world.devices["PC1"].interfaces["eth0"].ip is None
    grades = sess.check_all_tasks()
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "ENCOR DHCP gold lab must prove PC→gateway with verify.ping"
    assert any(not grades[t.id].is_correct for t in ping_tasks)

    _feed(
        sess,
        "R1",
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 10.30.30.1 255.255.255.0",
        "no shutdown",
        "exit",
        "ip dhcp pool CAMPUS",
        "network 10.30.30.0 255.255.255.0",
        "default-router 10.30.30.1",
        "end",
    )
    _feed(
        sess,
        "SW1",
        "enable",
        "configure terminal",
        "vlan 30",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport trunk encapsulation dot1q",
        "switchport mode trunk",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 30",
        "spanning-tree portfast",
        "end",
    )
    grades = sess.check_all_tasks()
    assert any(not grades[t.id].is_correct for t in ping_tasks)

    sess.world.shell("PC1").feed("ipconfig /renew")
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0
    leased = sess.world.devices["PC1"].interfaces["eth0"].ip
    assert leased is not None
    assert leased.startswith("10.30.30.")
    assert leased != "10.30.30.1"
