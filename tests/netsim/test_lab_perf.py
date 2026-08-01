"""NetSim performance and replay / ARP smoke tests."""

from __future__ import annotations

import time
from pathlib import Path

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.session import LabSession

ROOT = Path(__file__).resolve().parents[2]
SCALE_LAB = ROOT / "data" / "demo_labs" / "ccna_scale_campus_10.yaml"
BRANCH = ROOT / "data" / "demo_labs" / "ccna_branch_office_access.yaml"


def test_ten_device_lab_command_budget():
    lab = load_lab(SCALE_LAB)
    assert len(lab.topology.devices) >= 10
    session = LabSession.create(lab)
    names = session.world.device_names()
    commands = 0
    started = time.perf_counter()
    for name in names:
        shell = session.world.shell(name)
        for line in ("enable", "show version", "show ip interface brief"):
            shell.feed(line)
            commands += 1
        # Light ping against own loopback-ish connected IP when present.
        for iface in session.world.devices[name].interfaces.values():
            if iface.ip:
                shell.feed(f"ping {iface.ip}")
                commands += 1
                break
    elapsed = time.perf_counter() - started
    assert commands >= 30
    per = elapsed / commands
    assert per <= 0.1, f"{per:.4f}s/command exceeds 100ms budget ({commands} cmds)"


def test_command_log_and_replay_preserves_hostname():
    lab = load_lab(SCALE_LAB)
    session = LabSession.create(lab)
    session.world.shell("R1").feed("enable")
    session.world.shell("R1").feed("configure terminal")
    session.world.shell("R1").feed("hostname CAMPUS-R1")
    session.world.shell("R1").feed("end")
    assert any("hostname CAMPUS-R1" in line for _d, line in session.command_log)
    session.reset(replay=True)
    assert "hostname CAMPUS-R1" in session.world.devices["R1"].running_config()


def test_ping_learns_arp_entry():
    lab = load_lab(BRANCH)
    session = LabSession.create(lab)
    # Apply golden addressing so PC1 can reach gateway.
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    ):
        session.world.shell("R1").feed(line)
    for line in (
        "enable",
        "configure terminal",
        "vlan 10",
        "name USERS",
        "interface GigabitEthernet0/1",
        "switchport mode trunk",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 10",
        "interface GigabitEthernet0/3",
        "switchport mode access",
        "switchport access vlan 10",
        "end",
    ):
        session.world.shell("SW1").feed(line)
    session.world.shell("PC1").feed("ip address 10.10.10.10 255.255.255.0")
    session.world.shell("PC2").feed("ip address 10.10.10.20 255.255.255.0")
    out = session.world.ping("PC1", "10.10.10.1")
    assert "100 percent" in out
    arp = session.world.show_arp("PC1")
    assert "10.10.10.1" in arp


def test_branch_office_t4_verify_ping():
    lab = load_lab(BRANCH)
    t4 = next(t for t in lab.tasks if t.id == "t4")
    assert t4.verify is not None
    assert t4.verify.ping


def test_static_route_verify_ping():
    lab = load_lab(ROOT / "data" / "demo_labs" / "ccna_dual_router_static.yaml")
    session = LabSession.create(lab)
    session.world.shell("R1").feed("enable")
    session.world.shell("R1").feed("configure terminal")
    session.world.shell("R1").feed("ip route 192.168.2.0 255.255.255.0 172.16.0.2")
    session.world.shell("R1").feed("end")
    grade = session.check_current_task()
    assert grade.is_correct


def test_ospf_derived_route_ping():
    lab = load_lab(ROOT / "data" / "demo_labs" / "ccna_ospf_two_router.yaml")
    session = LabSession.create(lab)
    for line in (
        "enable",
        "configure terminal",
        "router ospf 1",
        "network 10.0.0.0 0.0.0.3 area 0",
        "network 192.168.1.0 0.0.0.255 area 0",
        "end",
    ):
        session.world.shell("R1").feed(line)
    for line in (
        "enable",
        "configure terminal",
        "router ospf 1",
        "network 10.0.0.0 0.0.0.3 area 0",
        "network 192.168.2.0 0.0.0.255 area 0",
        "end",
    ):
        session.world.shell("R2").feed(line)
    out = session.world.ping("R1", "192.168.2.1")
    assert "100 percent" in out
    route = session.world.devices["R1"].show_ip_route()
    assert "O " in route or "192.168.2.0" in route
    grade = session.check_current_task()
    assert grade.is_correct


def test_vlan_isolation_verify_blocks_cross_vlan_ping():
    lab = load_lab(ROOT / "data" / "demo_labs" / "ccna_vlan_isolation.yaml")
    session = LabSession.create(lab)
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/1",
        "switchport mode access",
        "switchport access vlan 10",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 20",
        "end",
    ):
        session.world.shell("SW1").feed(line)
    grade = session.check_current_task()
    assert grade.is_correct
    assert "0 percent" in session.world.ping("PC1", "10.10.10.20")
