#!/usr/bin/env python3
"""Generate graded CCNA demo labs (golden-solution friendly) for v0.2.x.

Writes YAML under data/demo_labs/. Keeps existing Branch Office lab intact.
Run: python scripts/generate_demo_labs.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo_labs"


def _lab(**kwargs):
    kwargs.setdefault("schema_version", 1)
    kwargs.setdefault("cert_tags", ["ccna"])
    kwargs.setdefault("pass_threshold", 1.0)
    return kwargs


LABS = [
    _lab(
        title="VLAN Access Ports",
        lab_id="ccna_vlan_access_ports",
        topic_code="2.1",
        difficulty=2,
        description="Create a user VLAN and place two access ports into it.",
        objectives=["Create VLAN 20", "Assign access ports"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On **SW1**, create **VLAN 20** named **SALES**.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["vlan 20", "name SALES"],
                },
            },
            {
                "id": "t2",
                "instructions": "Put Gi0/1 and Gi0/2 into VLAN 20 as access ports.",
                "grading_rules": {
                    "device": "SW1",
                    "require": [
                        "switchport mode access",
                        "switchport access vlan 20",
                    ],
                },
            },
        ],
        solution_config="vlan 20\n name SALES\ninterface GigabitEthernet0/1\n switchport mode access\n switchport access vlan 20\n",
    ),
    _lab(
        title="Trunk Uplink",
        lab_id="ccna_trunk_uplink",
        topic_code="2.1",
        difficulty=2,
        description="Configure a switch uplink as an 802.1Q trunk.",
        objectives=["Trunk Gi0/1"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": "GigabitEthernet0/1"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Configure SW1 Gi0/1 as a trunk.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["switchport mode trunk"],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/1\n switchport mode trunk\n",
    ),
    _lab(
        title="Router LAN Gateway",
        lab_id="ccna_router_lan_gateway",
        topic_code="1.1",
        difficulty=2,
        description="Address and enable a router LAN interface.",
        objectives=["Configure Gi0/0 10.0.0.1/24"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On R1 Gi0/0 set **10.0.0.1/24** and no shutdown.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "ip address 10.0.0.1 255.255.255.0",
                        "no shutdown",
                    ],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.0\n no shutdown\n",
    ),
    _lab(
        title="Static Default Route",
        lab_id="ccna_static_default_route",
        topic_code="3.1",
        difficulty=2,
        description="Add a default static route on R1.",
        objectives=["ip route 0.0.0.0 0.0.0.0 next-hop"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "172.16.0.1/30"},
                    ],
                    "base_config": "interface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.0\n no shutdown\ninterface GigabitEthernet0/1\n ip address 172.16.0.1 255.255.255.252\n no shutdown\n",
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Configure a default route via 172.16.0.2.",
                "grading_rules": {
                    "device": "R1",
                    "require": ["ip route 0.0.0.0 0.0.0.0 172.16.0.2"],
                },
            }
        ],
        solution_config="ip route 0.0.0.0 0.0.0.0 172.16.0.2\n",
    ),
    _lab(
        title="OSPFv2 Single Area",
        lab_id="ccna_ospfv2_single_area",
        topic_code="3.2",
        difficulty=3,
        description="Enable OSPF process 1 in area 0 on R1.",
        objectives=["router ospf 1", "network statement"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0", "ip": "10.1.1.1/24"}],
                    "base_config": "interface GigabitEthernet0/0\n ip address 10.1.1.1 255.255.255.0\n no shutdown\n",
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Start OSPF process 1 and advertise 10.1.1.0/24 in area 0.",
                "grading_rules": {
                    "device": "R1",
                    "require": ["router ospf 1", "network 10.1.1.0 0.0.0.255 area 0"],
                },
            }
        ],
        solution_config="router ospf 1\n network 10.1.1.0 0.0.0.255 area 0\n",
    ),
    _lab(
        title="Named ACL Basics",
        lab_id="ccna_acl_basics",
        topic_code="5.1",
        difficulty=3,
        description="Create a standard ACL denying a host.",
        objectives=["access-list deny host"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Create ACL 10 that denies host 10.10.10.50 then permits any.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "access-list 10 deny 10.10.10.50",
                        "access-list 10 permit any",
                    ],
                },
            }
        ],
        solution_config="access-list 10 deny 10.10.10.50\naccess-list 10 permit any\n",
    ),
    _lab(
        title="PAT Overload Outline",
        lab_id="ccna_nat_pat",
        topic_code="4.1",
        difficulty=3,
        description="Configure inside/outside interfaces and overload NAT.",
        objectives=["ip nat inside/outside", "overload"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [
                        {"name": "GigabitEthernet0/0"},
                        {"name": "GigabitEthernet0/1"},
                    ],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Mark Gi0/0 inside and Gi0/1 outside; add overload rule.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "ip nat inside",
                        "ip nat outside",
                        "ip nat inside source list 1 interface GigabitEthernet0/1 overload",
                    ],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/0\n ip nat inside\ninterface GigabitEthernet0/1\n ip nat outside\nip nat inside source list 1 interface GigabitEthernet0/1 overload\n",
    ),
    _lab(
        title="DHCP Pool",
        lab_id="ccna_dhcp_pool",
        topic_code="4.3",
        difficulty=3,
        description="Create an IOS DHCP pool for a LAN.",
        objectives=["ip dhcp pool"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Create DHCP pool LAN with network 192.168.10.0/24 and default-router 192.168.10.1.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "ip dhcp pool LAN",
                        "network 192.168.10.0 255.255.255.0",
                        "default-router 192.168.10.1",
                    ],
                },
            }
        ],
        solution_config="ip dhcp pool LAN\n network 192.168.10.0 255.255.255.0\n default-router 192.168.10.1\n",
    ),
    _lab(
        title="SSH VTY Hardening",
        lab_id="ccna_ssh_vty",
        topic_code="5.3",
        difficulty=3,
        description="Require SSH on VTY lines.",
        objectives=["transport input ssh"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On line vty 0 4 set transport input ssh.",
                "grading_rules": {
                    "device": "R1",
                    "require": ["transport input ssh"],
                },
            }
        ],
        solution_config="line vty 0 4\n transport input ssh\n",
    ),
    _lab(
        title="IPv6 Interface Addressing",
        lab_id="ccna_ipv6_addressing",
        topic_code="1.9",
        difficulty=3,
        description="Enable IPv6 and set a link address.",
        objectives=["ipv6 address"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Enable IPv6 unicast-routing and set Gi0/0 to 2001:db8:1::1/64.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "ipv6 unicast-routing",
                        "ipv6 address 2001:db8:1::1/64",
                    ],
                },
            }
        ],
        solution_config="ipv6 unicast-routing\ninterface GigabitEthernet0/0\n ipv6 address 2001:db8:1::1/64\n",
    ),
    _lab(
        title="EtherChannel Static",
        lab_id="ccna_etherchannel_static",
        topic_code="2.4",
        difficulty=3,
        description="Bundle two switch ports into a static Port-Channel.",
        objectives=["channel-group mode on"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Place Gi0/1 and Gi0/2 into channel-group 1 mode on.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["channel-group 1 mode on"],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/1\n channel-group 1 mode on\ninterface GigabitEthernet0/2\n channel-group 1 mode on\n",
    ),
    _lab(
        title="STP Portfast Edge",
        lab_id="ccna_stp_portfast",
        topic_code="2.5",
        difficulty=2,
        description="Enable PortFast on an access edge port.",
        objectives=["spanning-tree portfast"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": "GigabitEthernet0/2"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Enable spanning-tree portfast on Gi0/2.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["spanning-tree portfast"],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/2\n spanning-tree portfast\n",
    ),
    _lab(
        title="Inter-VLAN Router-on-a-Stick",
        lab_id="ccna_intervlan_roas",
        topic_code="3.3",
        difficulty=4,
        description="Create subinterfaces for VLAN 10 and 20.",
        objectives=["encapsulation dot1Q"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Configure Gi0/0.10 for VLAN 10 with 10.10.10.1/24.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "encapsulation dot1Q 10",
                        "ip address 10.10.10.1 255.255.255.0",
                    ],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/0.10\n encapsulation dot1Q 10\n ip address 10.10.10.1 255.255.255.0\n",
    ),
    _lab(
        title="Hostname and Banner",
        lab_id="ccna_hostname_banner",
        topic_code="4.1",
        difficulty=1,
        description="Set device identity basics.",
        objectives=["hostname", "banner"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Set hostname BRANCH1.",
                "grading_rules": {"device": "R1", "require": ["hostname BRANCH1"]},
            }
        ],
        solution_config="hostname BRANCH1\n",
    ),
    _lab(
        title="Switch Default Gateway",
        lab_id="ccna_switch_default_gateway",
        topic_code="1.1",
        difficulty=2,
        description="Set management default gateway on a L2 switch.",
        objectives=["ip default-gateway"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": "GigabitEthernet0/1"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Configure ip default-gateway 10.0.0.1 on SW1.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["ip default-gateway 10.0.0.1"],
                },
            }
        ],
        solution_config="ip default-gateway 10.0.0.1\n",
    ),
    _lab(
        title="Dual-Router Static Route",
        lab_id="ccna_dual_router_static",
        topic_code="3.1",
        difficulty=3,
        description="Add a specific static route between two routers.",
        objectives=["static route to remote LAN"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "172.16.0.1/30"},
                    ],
                    "base_config": "interface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.0\n no shutdown\ninterface GigabitEthernet0/1\n ip address 172.16.0.1 255.255.255.252\n no shutdown\n",
                },
                {
                    "name": "R2",
                    "type": "router",
                    "interfaces": [
                        {"name": "GigabitEthernet0/0", "ip": "172.16.0.2/30"},
                        {"name": "GigabitEthernet0/1", "ip": "192.168.2.1/24"},
                    ],
                    "base_config": "interface GigabitEthernet0/0\n ip address 172.16.0.2 255.255.255.252\n no shutdown\ninterface GigabitEthernet0/1\n ip address 192.168.2.1 255.255.255.0\n no shutdown\n",
                },
            ],
            "links": [{"a": "R1/GigabitEthernet0/1", "b": "R2/GigabitEthernet0/0"}],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On R1, add a static route to 192.168.2.0/24 via 172.16.0.2.",
                "grading_rules": {
                    "device": "R1",
                    "require": ["ip route 192.168.2.0 255.255.255.0 172.16.0.2"],
                },
            }
        ],
        solution_config="ip route 192.168.2.0 255.255.255.0 172.16.0.2\n",
    ),
    _lab(
        title="Access VLAN Isolation Check",
        lab_id="ccna_vlan_isolation",
        topic_code="2.1",
        difficulty=3,
        description="Place PCs in different VLANs; verify isolation intent via config.",
        objectives=["Different access VLANs"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Put Gi0/1 in VLAN 10 and Gi0/2 in VLAN 20 as access ports.",
                "grading_rules": {
                    "device": "SW1",
                    "require": [
                        "switchport access vlan 10",
                        "switchport access vlan 20",
                    ],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/1\n switchport access vlan 10\ninterface GigabitEthernet0/2\n switchport access vlan 20\n",
    ),
    _lab(
        title="Interface Descriptions",
        lab_id="ccna_interface_descriptions",
        topic_code="1.1",
        difficulty=1,
        description="Document an uplink with an interface description.",
        objectives=["description"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": "GigabitEthernet0/1"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "Set Gi0/1 description to UPLINK-TO-R1.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["description UPLINK-TO-R1"],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/1\n description UPLINK-TO-R1\n",
    ),
    _lab(
        title="Multi-task Campus Edge",
        lab_id="ccna_campus_edge",
        topic_code="2.1",
        difficulty=4,
        description="Combine VLAN, trunk, and gateway addressing tasks.",
        objectives=["VLAN", "trunk", "gateway"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                },
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                },
            ],
            "links": [{"a": "R1/GigabitEthernet0/0", "b": "SW1/GigabitEthernet0/1"}],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On R1 set Gi0/0 to 10.20.20.1/24 and no shut.",
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        "ip address 10.20.20.1 255.255.255.0",
                        "no shutdown",
                    ],
                },
            },
            {
                "id": "t2",
                "instructions": "On SW1 create VLAN 20 and trunk Gi0/1.",
                "grading_rules": {
                    "device": "SW1",
                    "require": ["vlan 20", "switchport mode trunk"],
                },
            },
        ],
        solution_config="hostname R1\ninterface GigabitEthernet0/0\n ip address 10.20.20.1 255.255.255.0\n no shutdown\nvlan 20\ninterface GigabitEthernet0/1\n switchport mode trunk\n",
    ),
]


def _vlan_variant(vlan: int, name: str, ports: tuple[str, str], difficulty: int = 2) -> dict:
    p1, p2 = ports
    return _lab(
        title=f"VLAN {vlan} Access ({name})",
        lab_id=f"ccna_vlan_{vlan}_{name.lower()}",
        topic_code="2.1",
        difficulty=difficulty,
        description=f"Create VLAN {vlan} ({name}) and assign two access ports.",
        objectives=[f"Create VLAN {vlan}", "Assign access ports"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": p1}, {"name": p2}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": f"On **SW1**, create **VLAN {vlan}** named **{name}**.",
                "grading_rules": {
                    "device": "SW1",
                    "require": [f"vlan {vlan}", f"name {name}"],
                },
            },
            {
                "id": "t2",
                "instructions": f"Put {p1} and {p2} into VLAN {vlan} as access ports.",
                "grading_rules": {
                    "device": "SW1",
                    "require": [
                        "switchport mode access",
                        f"switchport access vlan {vlan}",
                    ],
                },
            },
        ],
        solution_config=(
            f"vlan {vlan}\n name {name}\n"
            f"interface {p1}\n switchport mode access\n switchport access vlan {vlan}\n"
            f"interface {p2}\n switchport mode access\n switchport access vlan {vlan}\n"
        ),
    )


def _hostname_lab(device: str, hostname: str, topic: str, difficulty: int) -> dict:
    return _lab(
        title=f"Hostname {hostname}",
        lab_id=f"ccna_hostname_{hostname.lower()}",
        topic_code=topic,
        difficulty=difficulty,
        description=f"Set the device hostname to {hostname}.",
        objectives=[f"hostname {hostname}"],
        topology={
            "devices": [{"name": device, "type": "router", "interfaces": [{"name": "GigabitEthernet0/0"}]}],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": f"On **{device}**, set hostname to **{hostname}**.",
                "grading_rules": {"device": device, "require": [f"hostname {hostname}"]},
            }
        ],
        solution_config=f"hostname {hostname}\n",
    )


def _iface_address_lab(
    lab_id: str,
    title: str,
    ip: str,
    mask: str,
    topic: str,
    difficulty: int,
) -> dict:
    return _lab(
        title=title,
        lab_id=lab_id,
        topic_code=topic,
        difficulty=difficulty,
        description=f"Address Gi0/0 as {ip}/{mask} and bring it up.",
        objectives=["Interface addressing", "no shutdown"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": (
                    f"On **R1**, set Gi0/0 to **{ip}** with mask **{mask}** and no shut."
                ),
                "grading_rules": {
                    "device": "R1",
                    "require": [f"ip address {ip} {mask}", "no shutdown"],
                },
            }
        ],
        solution_config=(
            f"interface GigabitEthernet0/0\n ip address {ip} {mask}\n no shutdown\n"
        ),
    )


def _static_route_lab(lab_id: str, network: str, mask: str, nh: str, difficulty: int) -> dict:
    return _lab(
        title=f"Static Route {network}",
        lab_id=lab_id,
        topic_code="3.1",
        difficulty=difficulty,
        description=f"Add a static route for {network}/{mask} via {nh}.",
        objectives=["ip route"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": f"On **R1**, add ``ip route {network} {mask} {nh}``.",
                "grading_rules": {
                    "device": "R1",
                    "require": [f"ip route {network} {mask} {nh}"],
                },
            }
        ],
        solution_config=f"ip route {network} {mask} {nh}\n",
    )


def _acl_lab(lab_id: str, acl: int, deny_host: str, difficulty: int) -> dict:
    return _lab(
        title=f"ACL {acl} Deny Host",
        lab_id=lab_id,
        topic_code="5.1",
        difficulty=difficulty,
        description=f"Create standard ACL {acl} denying host {deny_host}.",
        objectives=[f"access-list {acl}"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": (
                    f"On **R1**, create ACL **{acl}** denying host **{deny_host}** "
                    "then permit any."
                ),
                "grading_rules": {
                    "device": "R1",
                    "require": [
                        f"access-list {acl} deny host {deny_host}",
                        f"access-list {acl} permit any",
                    ],
                },
            }
        ],
        solution_config=(
            f"access-list {acl} deny host {deny_host}\naccess-list {acl} permit any\n"
        ),
    )


def _desc_lab(lab_id: str, iface: str, description: str, difficulty: int) -> dict:
    return _lab(
        title=f"Interface Description {description}",
        lab_id=lab_id,
        topic_code="1.1",
        difficulty=difficulty,
        description=f"Set {iface} description to {description}.",
        objectives=["interface description"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": iface}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": f"On **SW1**, set {iface} description to **{description}**.",
                "grading_rules": {
                    "device": "SW1",
                    "require": [f"description {description}"],
                },
            }
        ],
        solution_config=f"interface {iface}\n description {description}\n",
    )


# Procedural variants to reach the v0.4 ≥50 lab catalog target.
_VARIANT_LABS = [
    _vlan_variant(30, "ENG", ("GigabitEthernet0/1", "GigabitEthernet0/2"), 2),
    _vlan_variant(40, "GUEST", ("GigabitEthernet0/1", "GigabitEthernet0/3"), 2),
    _vlan_variant(50, "VOICE", ("GigabitEthernet0/2", "GigabitEthernet0/3"), 3),
    _vlan_variant(60, "IOT", ("GigabitEthernet0/1", "GigabitEthernet0/4"), 2),
    _vlan_variant(70, "LAB", ("GigabitEthernet0/2", "GigabitEthernet0/4"), 2),
    _hostname_lab("R1", "EDGE-R1", "1.1", 1),
    _hostname_lab("R1", "CORE-R1", "1.1", 1),
    _hostname_lab("R1", "BR-R1", "1.1", 1),
    _hostname_lab("R1", "HQ-R1", "1.1", 1),
    _iface_address_lab(
        "ccna_iface_192_168_10", "LAN Addressing 192.168.10.1", "192.168.10.1", "255.255.255.0", "1.1", 2
    ),
    _iface_address_lab(
        "ccna_iface_192_168_20", "LAN Addressing 192.168.20.1", "192.168.20.1", "255.255.255.0", "1.1", 2
    ),
    _iface_address_lab(
        "ccna_iface_10_0_0_1", "LAN Addressing 10.0.0.1", "10.0.0.1", "255.255.255.0", "1.1", 2
    ),
    _iface_address_lab(
        "ccna_iface_172_16_0_1", "LAN Addressing 172.16.0.1", "172.16.0.1", "255.255.255.0", "1.1", 2
    ),
    _static_route_lab("ccna_static_10_20", "10.20.0.0", "255.255.0.0", "192.168.1.2", 2),
    _static_route_lab("ccna_static_10_30", "10.30.0.0", "255.255.0.0", "192.168.1.2", 2),
    _static_route_lab("ccna_static_172_16", "172.16.0.0", "255.255.0.0", "10.0.0.2", 3),
    _static_route_lab("ccna_static_default_alt", "0.0.0.0", "0.0.0.0", "203.0.113.1", 2),
    _acl_lab("ccna_acl_20", 20, "10.10.10.50", 3),
    _acl_lab("ccna_acl_30", 30, "192.168.5.5", 3),
    _acl_lab("ccna_acl_40", 40, "172.16.1.10", 3),
    _desc_lab("ccna_desc_uplink_core", "GigabitEthernet0/1", "UPLINK-CORE", 1),
    _desc_lab("ccna_desc_to_wan", "GigabitEthernet0/1", "TO-WAN", 1),
    _desc_lab("ccna_desc_to_access", "GigabitEthernet0/2", "TO-ACCESS", 1),
    _desc_lab("ccna_desc_mgmt", "GigabitEthernet0/1", "MGMT-ONLY", 1),
    _lab(
        title="SSH Login Banner",
        lab_id="ccna_banner_ssh",
        topic_code="5.3",
        difficulty=2,
        description="Configure an MOTD banner for login messaging.",
        objectives=["banner motd"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On **R1**, set banner motd to **AUTHORIZED ONLY**.",
                "grading_rules": {
                    "device": "R1",
                    "require": ["banner motd", "AUTHORIZED ONLY"],
                },
            }
        ],
        solution_config="banner motd ^AUTHORIZED ONLY^\n",
    ),
    _lab(
        title="OSPFv2 Router ID Prep",
        lab_id="ccna_ospf_router_id",
        topic_code="3.2",
        difficulty=3,
        description="Start OSPF process 1 and set a stable router-id.",
        objectives=["router ospf", "router-id"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On **R1**, configure ``router ospf 1`` with router-id **1.1.1.1**.",
                "grading_rules": {
                    "device": "R1",
                    "require": ["router ospf 1", "router-id 1.1.1.1"],
                },
            }
        ],
        solution_config="router ospf 1\n router-id 1.1.1.1\n",
    ),
    _lab(
        title="DHCP Excluded Addresses",
        lab_id="ccna_dhcp_excluded",
        topic_code="4.3",
        difficulty=2,
        description="Exclude a range from a DHCP pool.",
        objectives=["ip dhcp excluded-address"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": (
                    "On **R1**, exclude **192.168.10.1** through **192.168.10.10** "
                    "from DHCP."
                ),
                "grading_rules": {
                    "device": "R1",
                    "require": ["ip dhcp excluded-address 192.168.10.1 192.168.10.10"],
                },
            }
        ],
        solution_config="ip dhcp excluded-address 192.168.10.1 192.168.10.10\n",
    ),
    _lab(
        title="NAT Inside Interface Mark",
        lab_id="ccna_nat_inside_mark",
        topic_code="4.1",
        difficulty=3,
        description="Mark Gi0/0 as ip nat inside.",
        objectives=["ip nat inside"],
        topology={
            "devices": [
                {
                    "name": "R1",
                    "type": "router",
                    "interfaces": [{"name": "GigabitEthernet0/0"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": "On **R1**, configure Gi0/0 with ``ip nat inside``.",
                "grading_rules": {"device": "R1", "require": ["ip nat inside"]},
            }
        ],
        solution_config="interface GigabitEthernet0/0\n ip nat inside\n",
    ),
    _lab(
        title="Trunk Native VLAN 99",
        lab_id="ccna_trunk_native_99",
        topic_code="2.1",
        difficulty=3,
        description="Configure a trunk and set native VLAN 99.",
        objectives=["trunk", "native vlan"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": "GigabitEthernet0/1"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": (
                    "On **SW1**, make Gi0/1 a trunk with native VLAN **99**."
                ),
                "grading_rules": {
                    "device": "SW1",
                    "require": [
                        "switchport mode trunk",
                        "switchport trunk native vlan 99",
                    ],
                },
            }
        ],
        solution_config=(
            "interface GigabitEthernet0/1\n"
            " switchport mode trunk\n"
            " switchport trunk native vlan 99\n"
        ),
    ),
    _lab(
        title="EtherChannel Mode Active",
        lab_id="ccna_etherchannel_active",
        topic_code="2.4",
        difficulty=3,
        description="Bundle Gi0/1 into a channel-group with mode active.",
        objectives=["channel-group"],
        topology={
            "devices": [
                {
                    "name": "SW1",
                    "type": "switch",
                    "interfaces": [{"name": "GigabitEthernet0/1"}],
                }
            ],
            "links": [],
        },
        tasks=[
            {
                "id": "t1",
                "instructions": (
                    "On **SW1**, put Gi0/1 in ``channel-group 1 mode active``."
                ),
                "grading_rules": {
                    "device": "SW1",
                    "require": ["channel-group 1 mode active"],
                },
            }
        ],
        solution_config="interface GigabitEthernet0/1\n channel-group 1 mode active\n",
    ),
]

LABS.extend(_VARIANT_LABS)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    for lab in LABS:
        path = OUT / f"{lab['lab_id']}.yaml"
        if path.exists() and lab["lab_id"] == "ccna_branch_office_access":
            continue
        path.write_text(yaml.safe_dump(lab, sort_keys=False, allow_unicode=True), encoding="utf-8")
        written += 1
    # Ensure branch office remains
    existing = list(OUT.glob("*.yaml"))
    print(f"Wrote {written} labs; total lab files now {len(existing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
