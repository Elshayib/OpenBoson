"""Shared helpers for the branch-office gold lab."""

from openboson.netsim.session import LabSession


def apply_branch_solution(session: LabSession) -> None:
    """Feed the branch-office golden solution into the live OpenIOS world."""
    for line in (
        "enable",
        "configure terminal",
        "hostname R1",
        "interface GigabitEthernet0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    ):
        session.world.shell("R1").feed(line)
    for line in (
        "enable",
        "configure terminal",
        "hostname SW1",
        "vlan 10",
        "name USERS",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport trunk encapsulation dot1q",
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
