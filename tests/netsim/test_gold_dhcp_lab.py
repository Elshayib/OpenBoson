"""Live-grade DHCP gold lab: ping fails until the PC renews a lease."""

from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab

LAB = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_dhcp_pool_lan.yaml"


def _feed(session: LabSession, device: str, *lines: str) -> None:
    shell = session.world.shell(device)
    for line in lines:
        shell.feed(line)


def test_dhcp_lab_fails_before_renew_and_passes_after():
    lab = load_lab(LAB)
    sess = LabSession.create(lab)
    assert sess.world.devices["PC1"].interfaces["eth0"].ip is None
    grades = sess.check_all_tasks()
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "DHCP gold lab must prove PC→gateway with verify.ping"
    assert any(not grades[t.id].is_correct for t in ping_tasks)
    assert all(
        p.source == "PC1" and p.destination == "192.168.10.1"
        for t in ping_tasks
        for p in t.verify.ping
    )

    _feed(
        sess,
        "R1",
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 192.168.10.1 255.255.255.0",
        "no shutdown",
        "exit",
        "ip dhcp pool LAN",
        "network 192.168.10.0 255.255.255.0",
        "default-router 192.168.10.1",
        "end",
    )
    _feed(
        sess,
        "SW1",
        "enable",
        "configure terminal",
        "vlan 10",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport trunk encapsulation dot1q",
        "switchport mode trunk",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 10",
        "spanning-tree portfast",
        "end",
    )
    grades = sess.check_all_tasks()
    assert any(not grades[t.id].is_correct for t in ping_tasks)
    assert sess.world.devices["PC1"].interfaces["eth0"].ip is None

    sess.world.shell("PC1").feed("ipconfig /renew")
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0
    leased = sess.world.devices["PC1"].interfaces["eth0"].ip
    assert leased is not None
    assert leased.startswith("192.168.10.")
    assert leased != "192.168.10.1"
