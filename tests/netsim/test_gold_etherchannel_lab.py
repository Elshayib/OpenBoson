"""Live-grade EtherChannel gold lab: ping survives shutting one bundle member."""

from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession, score_lab

LAB = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_etherchannel_campus.yaml"


def _feed(session: LabSession, device: str, *lines: str) -> None:
    shell = session.world.shell(device)
    for line in lines:
        shell.feed(line)


def _prep_access_vlan_and_trunks(session: LabSession) -> None:
    for sw in ("SW1", "SW2"):
        _feed(
            session,
            sw,
            "enable",
            "configure terminal",
            "vlan 10",
            "exit",
            "interface GigabitEthernet0/3",
            "switchport mode access",
            "switchport access vlan 10",
            "spanning-tree portfast",
            "no shutdown",
            "interface GigabitEthernet0/1",
            "switchport mode trunk",
            "no shutdown",
            "interface GigabitEthernet0/2",
            "switchport mode trunk",
            "no shutdown",
            "end",
        )


def _shut_forwarding_member(session: LabSession) -> None:
    """Shut the unbundled forwarding link (lowest local interface name)."""
    _feed(
        session,
        "SW1",
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/1",
        "shutdown",
        "end",
    )


def _bundle_members(session: LabSession) -> None:
    for sw in ("SW1", "SW2"):
        _feed(
            session,
            sw,
            "enable",
            "configure terminal",
            "interface GigabitEthernet0/1",
            "channel-group 1 mode on",
            "interface GigabitEthernet0/2",
            "channel-group 1 mode on",
            "end",
        )


def test_etherchannel_lab_fails_unbundled_after_member_shut_and_passes_after_bundle():
    lab = load_lab(LAB)
    sess = LabSession.create(lab)
    ping_tasks = [t for t in lab.tasks if t.verify and t.verify.ping]
    assert ping_tasks, "EtherChannel gold lab must prove PC1→PC2 with verify.ping"
    assert all(
        p.source == "PC1" and p.destination == "10.10.10.20"
        for t in ping_tasks
        for p in t.verify.ping
    )

    _prep_access_vlan_and_trunks(sess)
    assert "100 percent" in sess.world.ping("PC1", "10.10.10.20")
    _shut_forwarding_member(sess)
    grades = sess.check_all_tasks()
    assert any(not grades[t.id].is_correct for t in ping_tasks)
    assert "Success rate is 0 percent" in sess.world.ping("PC1", "10.10.10.20")

    _bundle_members(sess)
    sess.check_all_tasks()
    result = score_lab(sess)
    assert result.score == 1.0
    assert "100 percent" in sess.world.ping("PC1", "10.10.10.20")
