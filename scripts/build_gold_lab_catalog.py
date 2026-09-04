#!/usr/bin/env python3
"""Rebuild data/demo_labs for the Labs Experience Rework (gold / drill / scale).

Deletes existing data/demo_labs/*.yaml then writes a curated catalog.
Run: python scripts/build_gold_lab_catalog.py
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
    kwargs.setdefault("lab_tier", "gold")
    kwargs.setdefault("difficulty", 3)
    kwargs.setdefault("objectives", [])
    kwargs.setdefault("description", "")
    return kwargs


def _dev(name: str, dtype: str, ifaces: list[dict], base_config: str | None = None) -> dict:
    d: dict = {"name": name, "type": dtype, "interfaces": ifaces}
    if base_config is not None:
        d["base_config"] = base_config
    return d


def _link(a: str, b: str) -> dict:
    return {"a": a, "b": b}


def _task(
    tid: str,
    instructions: str,
    *,
    device: str | None = None,
    require: list[str] | None = None,
    verify_ping: list[dict] | None = None,
    verify_show: list[dict] | None = None,
    expected_config: str | None = None,
) -> dict:
    t: dict = {"id": tid, "instructions": instructions}
    if expected_config is not None:
        t["expected_config"] = expected_config
    if require is not None or device is not None:
        rules: dict = {}
        if device is not None:
            rules["device"] = device
        if require is not None:
            rules["require"] = require
        t["grading_rules"] = rules
    if verify_ping or verify_show:
        block: dict = {}
        if verify_ping:
            block["ping"] = verify_ping
        if verify_show:
            block["show"] = verify_show
        t["verify"] = block
    return t


def _ping(source: str, destination: str, should_succeed: bool = True) -> dict:
    return {
        "source": source,
        "destination": destination,
        "should_succeed": should_succeed,
    }


def _show(device: str, *contains: str) -> dict:
    return {"device": device, "contains": list(contains)}


# ---------------------------------------------------------------------------
# Archetypes (preserve lab_id / addressing used by tests)
# ---------------------------------------------------------------------------


def lab_branch_office() -> dict:
    return _lab(
        title="Branch Office Access",
        lab_id="ccna_branch_office_access",
        topic_code="2.1",
        difficulty=3,
        description=(
            "Configure a small branch site so two user PCs on a switch can reach "
            "each other and their default gateway on the router."
        ),
        objectives=[
            "Place R1's LAN interface into service with the correct address.",
            "Build the user VLAN and trunk the switch uplink toward the router.",
            "Address both PCs on the user subnet and prove reachability.",
        ],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "connected_to": "SW1/GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/1"},
                    ],
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "R1/GigabitEthernet0/0"},
                        {"name": "GigabitEthernet0/2", "connected_to": "PC1/eth0"},
                        {"name": "GigabitEthernet0/3", "connected_to": "PC2/eth0"},
                    ],
                ),
                _dev("PC1", "pc", [{"name": "eth0", "connected_to": "SW1/GigabitEthernet0/2"}]),
                _dev("PC2", "pc", [{"name": "eth0", "connected_to": "SW1/GigabitEthernet0/3"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
                _link("SW1/GigabitEthernet0/3", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**R1 — LAN gateway**\n\n"
                "R1's GigabitEthernet0/0 must be **10.10.10.1/24** and operational "
                "so it can serve as the default gateway for the user subnet.",
                device="R1",
                require=["ip address 10.10.10.1 255.255.255.0", "no shutdown"],
                expected_config=(
                    "hostname R1\n"
                    "interface GigabitEthernet0/0\n"
                    " ip address 10.10.10.1 255.255.255.0\n"
                    " no shutdown\n"
                ),
            ),
            _task(
                "t2",
                "**SW1 — user VLAN and uplink**\n\n"
                "Create **VLAN 10** named **USERS**. The link toward R1 must carry "
                "that traffic as a trunk. Access ports toward the PCs belong in VLAN 10.",
                device="SW1",
                require=[
                    "vlan 10",
                    "name USERS",
                    "switchport mode trunk",
                    "switchport access vlan 10",
                ],
                expected_config=(
                    "vlan 10\n name USERS\n"
                    "interface GigabitEthernet0/1\n switchport mode trunk\n"
                    "interface GigabitEthernet0/2\n switchport mode access\n"
                    " switchport access vlan 10\n"
                    "interface GigabitEthernet0/3\n switchport mode access\n"
                    " switchport access vlan 10\n"
                ),
            ),
            _task(
                "t3",
                "**PC1 and PC2 — host addressing**\n\n"
                "PC1 must be **10.10.10.10/24**. PC2 must be **10.10.10.20/24**. "
                "Both hosts share gateway **10.10.10.1**.",
                require=[
                    "ip address 10.10.10.10 255.255.255.0",
                    "ip address 10.10.10.20 255.255.255.0",
                ],
            ),
            _task(
                "t4",
                "**Verification — end-to-end**\n\n"
                "From **PC1**, the gateway **10.10.10.1** and **PC2** (**10.10.10.20**) "
                "must be reachable.",
                require=[
                    "ip address 10.10.10.1 255.255.255.0",
                    "vlan 10",
                    "ip address 10.10.10.10 255.255.255.0",
                    "ip address 10.10.10.20 255.255.255.0",
                ],
                verify_ping=[
                    _ping("PC1", "10.10.10.1"),
                    _ping("PC1", "10.10.10.20"),
                ],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "hostname R1\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.10.10.1 255.255.255.0\n"
            " no shutdown\n"
            "! --- SW1 ---\n"
            "hostname SW1\n"
            "vlan 10\n"
            " name USERS\n"
            "interface GigabitEthernet0/1\n"
            " switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            "interface GigabitEthernet0/3\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            "! --- PC1 ---\n"
            "ip address 10.10.10.10 255.255.255.0\n"
            "! --- PC2 ---\n"
            "ip address 10.10.10.20 255.255.255.0\n"
        ),
    )


def lab_vlan_isolation() -> dict:
    return _lab(
        title="Access VLAN Isolation Check",
        lab_id="ccna_vlan_isolation",
        topic_code="2.1",
        description="Place PCs in different VLANs and verify they cannot reach each other.",
        objectives=["Different access VLANs", "L2 isolation via ping", "Name the VLANs"],
        topology={
            "devices": [
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                _dev(
                    "PC2",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.20/24"}],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("PC1/eth0", "SW1/GigabitEthernet0/1"),
                _link("PC2/eth0", "SW1/GigabitEthernet0/2"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Put **Gi0/1** in VLAN 10 and **Gi0/2** in VLAN 20 as access ports. "
                "PC1 and PC2 share the same IP subnet but must **not** reach each other.",
                device="SW1",
                require=["switchport access vlan 10", "switchport access vlan 20"],
                verify_ping=[_ping("PC1", "10.10.10.20", False)],
            ),
            _task(
                "t2",
                "Create **VLAN 10** named **USERS** and **VLAN 20** named **GUEST**.",
                device="SW1",
                require=["vlan 10", "name USERS", "vlan 20", "name GUEST"],
            ),
            _task(
                "t3",
                "Set the switch hostname to **ISO-SW1**.",
                device="SW1",
                require=["hostname ISO-SW1"],
                verify_show=[_show("SW1", "hostname ISO-SW1")],
            ),
        ],
        solution_config=(
            "hostname ISO-SW1\n"
            "vlan 10\n name USERS\n"
            "vlan 20\n name GUEST\n"
            "interface GigabitEthernet0/1\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 20\n"
        ),
    )


def lab_dual_router_static() -> dict:
    r1_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.0.0.1 255.255.255.0\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 172.16.0.1 255.255.255.252\n"
        " no shutdown\n"
    )
    r2_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 172.16.0.2 255.255.255.252\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 192.168.2.1 255.255.255.0\n"
        " no shutdown\n"
    )
    return _lab(
        title="Dual-Router Static Route",
        lab_id="ccna_dual_router_static",
        topic_code="3.1",
        description="Add a specific static route between two routers and verify reachability.",
        objectives=["static route to remote LAN", "ping via next-hop", "address PC1"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "172.16.0.1/30"},
                    ],
                    base_config=r1_base,
                ),
                _dev(
                    "R2",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "172.16.0.2/30"},
                        {"name": "GigabitEthernet0/1", "ip": "192.168.2.1/24"},
                    ],
                    base_config=r2_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "192.168.2.10/24"}],
                    base_config="ip address 192.168.2.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/1", "R2/GigabitEthernet0/0"),
                _link("R2/GigabitEthernet0/1", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On R1, add a static route to **192.168.2.0/24** via **172.16.0.2**. "
                "Verify R1 can ping **192.168.2.1**.",
                device="R1",
                require=["ip route 192.168.2.0 255.255.255.0 172.16.0.2"],
                verify_ping=[_ping("R1", "192.168.2.1")],
            ),
            _task(
                "t2",
                "On R2, add a return static route to **10.0.0.0/24** via **172.16.0.1**.",
                device="R2",
                require=["ip route 10.0.0.0 255.255.255.0 172.16.0.1"],
            ),
            _task(
                "t3",
                "Confirm R1 can reach **PC1** at **192.168.2.10**.",
                device="R1",
                require=["ip route 192.168.2.0 255.255.255.0 172.16.0.2"],
                verify_ping=[_ping("R1", "192.168.2.10")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "ip route 192.168.2.0 255.255.255.0 172.16.0.2\n"
            "! --- R2 ---\n"
            "ip route 10.0.0.0 255.255.255.0 172.16.0.1\n"
            "! --- PC1 ---\n"
            "ip address 192.168.2.10 255.255.255.0\n"
        ),
    )


def lab_ospf_two_router() -> dict:
    r1_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.0.0.1 255.255.255.252\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 192.168.1.1 255.255.255.0\n"
        " no shutdown\n"
    )
    r2_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.0.0.2 255.255.255.252\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 192.168.2.1 255.255.255.0\n"
        " no shutdown\n"
    )
    return _lab(
        title="OSPF Two-Router Reachability",
        lab_id="ccna_ospf_two_router",
        topic_code="3.2",
        difficulty=4,
        description="Enable OSPF on adjacent routers and verify remote LAN reachability.",
        objectives=["OSPFv2 adjacency", "network statements", "ping remote LAN via OSPF"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/30"},
                        {"name": "GigabitEthernet0/1", "ip": "192.168.1.1/24"},
                    ],
                    base_config=r1_base,
                ),
                _dev(
                    "R2",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.2/30"},
                        {"name": "GigabitEthernet0/1", "ip": "192.168.2.1/24"},
                    ],
                    base_config=r2_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "192.168.2.10/24"}],
                    base_config="ip address 192.168.2.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "R2/GigabitEthernet0/0"),
                _link("R2/GigabitEthernet0/1", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **R1** and **R2**, start OSPF process 1 and advertise both local networks "
                "in area 0 (link `10.0.0.0/30` and each LAN). Then verify R1 can ping "
                "**192.168.2.1**.",
                require=[
                    "router ospf 1",
                    "network 10.0.0.0 0.0.0.3 area 0",
                    "network 192.168.1.0 0.0.0.255 area 0",
                    "network 192.168.2.0 0.0.0.255 area 0",
                ],
                verify_ping=[_ping("R1", "192.168.2.1")],
            ),
            _task(
                "t2",
                "Set hostname **OSPF-R1** on R1 and **OSPF-R2** on R2.",
                require=["hostname OSPF-R1", "hostname OSPF-R2"],
            ),
            _task(
                "t3",
                "Confirm R1 can reach **PC1** at **192.168.2.10** via OSPF.",
                require=["router ospf 1", "network 192.168.2.0 0.0.0.255 area 0"],
                verify_ping=[_ping("R1", "192.168.2.10")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "hostname OSPF-R1\n"
            "router ospf 1\n"
            " network 10.0.0.0 0.0.0.3 area 0\n"
            " network 192.168.1.0 0.0.0.255 area 0\n"
            "! --- R2 ---\n"
            "hostname OSPF-R2\n"
            "router ospf 1\n"
            " network 10.0.0.0 0.0.0.3 area 0\n"
            " network 192.168.2.0 0.0.0.255 area 0\n"
            "! --- PC1 ---\n"
            "ip address 192.168.2.10 255.255.255.0\n"
        ),
    )


# ---------------------------------------------------------------------------
# Additional gold scenarios
# ---------------------------------------------------------------------------


def lab_trunk_campus() -> dict:
    return _lab(
        title="Trunk Campus Pair",
        lab_id="ccna_trunk_campus",
        topic_code="2.1",
        description="Trunk two access switches and place a PC in the user VLAN.",
        objectives=["Create VLAN 10", "Trunk SW1-SW2", "Access port for PC1"],
        topology={
            "devices": [
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                ),
                _dev(
                    "SW2",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("SW1/GigabitEthernet0/1", "SW2/GigabitEthernet0/1"),
                _link("SW2/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **SW1** and **SW2**, create **VLAN 10** named **USERS**.",
                require=["vlan 10", "name USERS"],
            ),
            _task(
                "t2",
                "Trunk **Gi0/1** on both switches toward each other.",
                require=["switchport mode trunk"],
                verify_show=[_show("SW1", "switchport mode trunk")],
            ),
            _task(
                "t3",
                "On **SW2**, put **Gi0/2** in VLAN 10 as an access port.",
                device="SW2",
                require=["switchport mode access", "switchport access vlan 10"],
            ),
        ],
        solution_config=(
            "! --- SW1 ---\n"
            "vlan 10\n name USERS\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "! --- SW2 ---\n"
            "vlan 10\n name USERS\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
        ),
    )


def lab_intervlan_roas() -> dict:
    """Router-on-a-stick style: subinterfaces + trunk + PC gateway ping."""
    return _lab(
        title="ROAS Inter-VLAN Gateway",
        lab_id="ccna_intervlan_roas",
        topic_code="3.3",
        difficulty=4,
        description="Address ROAS subinterfaces and prove a PC can reach its gateway.",
        objectives=["Subinterface addressing", "Trunk uplink", "PC gateway ping"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0"},
                        {"name": "GigabitEthernet0/0.10"},
                        {"name": "GigabitEthernet0/0.20"},
                    ],
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                    ],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **R1**, address **Gi0/0.10** as **10.10.10.1/24** and bring it up. "
                "Also no-shut the parent **Gi0/0**.",
                device="R1",
                require=["ip address 10.10.10.1 255.255.255.0", "no shutdown"],
            ),
            _task(
                "t2",
                "On **SW1**, create VLAN 10, trunk **Gi0/1**, and put **Gi0/2** in VLAN 10.",
                device="SW1",
                require=["vlan 10", "switchport mode trunk", "switchport access vlan 10"],
            ),
            _task(
                "t3",
                "Address **PC1** as **10.10.10.10/24** and ping the gateway **10.10.10.1**.",
                require=["ip address 10.10.10.10 255.255.255.0"],
                verify_ping=[_ping("PC1", "10.10.10.1")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "interface GigabitEthernet0/0\n no shutdown\n"
            "interface GigabitEthernet0/0.10\n"
            " ip address 10.10.10.1 255.255.255.0\n"
            " no shutdown\n"
            "! --- SW1 ---\n"
            "vlan 10\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            "! --- PC1 ---\n"
            "ip address 10.10.10.10 255.255.255.0\n"
        ),
    )


def lab_static_default_edge() -> dict:
    r1_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.0.0.1 255.255.255.0\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 172.16.0.1 255.255.255.252\n"
        " no shutdown\n"
    )
    isp_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 172.16.0.2 255.255.255.252\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 8.8.8.1 255.255.255.0\n"
        " no shutdown\n"
    )
    return _lab(
        title="Static Default Edge",
        lab_id="ccna_static_default_edge",
        topic_code="3.1",
        description="Point a branch edge router at ISP with a default static route.",
        objectives=["Default route", "Return route", "Ping ISP LAN"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "172.16.0.1/30"},
                    ],
                    base_config=r1_base,
                ),
                _dev(
                    "ISP",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "172.16.0.2/30"},
                        {"name": "GigabitEthernet0/1", "ip": "8.8.8.1/24"},
                    ],
                    base_config=isp_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.0.0.10/24"}],
                    base_config="ip address 10.0.0.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/1", "ISP/GigabitEthernet0/0"),
                _link("R1/GigabitEthernet0/0", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **R1**, add a default route via **172.16.0.2**.",
                device="R1",
                require=["ip route 0.0.0.0 0.0.0.0 172.16.0.2"],
            ),
            _task(
                "t2",
                "On **ISP**, add a route to **10.0.0.0/24** via **172.16.0.1**.",
                device="ISP",
                require=["ip route 10.0.0.0 255.255.255.0 172.16.0.1"],
            ),
            _task(
                "t3",
                "Verify **R1** can ping **8.8.8.1**.",
                device="R1",
                require=["ip route 0.0.0.0 0.0.0.0 172.16.0.2"],
                verify_ping=[_ping("R1", "8.8.8.1")],
            ),
        ],
        solution_config=(
            "ip route 0.0.0.0 0.0.0.0 172.16.0.2\nip route 10.0.0.0 255.255.255.0 172.16.0.1\n"
        ),
    )


def lab_ospf_three_router() -> dict:
    def _rbase(wan_ip: str, lan_ip: str) -> str:
        return (
            "interface GigabitEthernet0/0\n"
            f" ip address {wan_ip} 255.255.255.252\n"
            " no shutdown\n"
            "interface GigabitEthernet0/1\n"
            f" ip address {lan_ip} 255.255.255.0\n"
            " no shutdown\n"
        )

    return _lab(
        title="OSPF Three-Router Ring",
        lab_id="ccna_ospf_three_router",
        topic_code="3.2",
        difficulty=4,
        description="Form a three-router OSPF area and reach a PC on R3.",
        objectives=["OSPF on three routers", "Advertise LANs", "Ping PC1"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/30"},
                        {"name": "GigabitEthernet0/1", "ip": "192.168.1.1/24"},
                    ],
                    base_config=_rbase("10.0.0.1", "192.168.1.1"),
                ),
                _dev(
                    "R2",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.2/30"},
                        {"name": "GigabitEthernet0/1", "ip": "10.0.0.5/30"},
                    ],
                    base_config=(
                        "interface GigabitEthernet0/0\n"
                        " ip address 10.0.0.2 255.255.255.252\n"
                        " no shutdown\n"
                        "interface GigabitEthernet0/1\n"
                        " ip address 10.0.0.5 255.255.255.252\n"
                        " no shutdown\n"
                    ),
                ),
                _dev(
                    "R3",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.6/30"},
                        {"name": "GigabitEthernet0/1", "ip": "192.168.3.1/24"},
                    ],
                    base_config=_rbase("10.0.0.6", "192.168.3.1"),
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "192.168.3.10/24"}],
                    base_config="ip address 192.168.3.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "R2/GigabitEthernet0/0"),
                _link("R2/GigabitEthernet0/1", "R3/GigabitEthernet0/0"),
                _link("R3/GigabitEthernet0/1", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Enable **router ospf 1** on R1/R2/R3 and advertise the transit links "
                "plus R1/R3 LANs in area 0.",
                require=[
                    "router ospf 1",
                    "network 10.0.0.0 0.0.0.3 area 0",
                    "network 10.0.0.4 0.0.0.3 area 0",
                    "network 192.168.1.0 0.0.0.255 area 0",
                    "network 192.168.3.0 0.0.0.255 area 0",
                ],
            ),
            _task(
                "t2",
                "Confirm R1 can ping R3's LAN gateway **192.168.3.1**.",
                require=["router ospf 1"],
                verify_ping=[_ping("R1", "192.168.3.1")],
            ),
            _task(
                "t3",
                "Confirm R1 can ping **PC1** at **192.168.3.10**.",
                require=["network 192.168.3.0 0.0.0.255 area 0"],
                verify_ping=[_ping("R1", "192.168.3.10")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "router ospf 1\n"
            " network 10.0.0.0 0.0.0.3 area 0\n"
            " network 192.168.1.0 0.0.0.255 area 0\n"
            "! --- R2 ---\n"
            "router ospf 1\n"
            " network 10.0.0.0 0.0.0.3 area 0\n"
            " network 10.0.0.4 0.0.0.3 area 0\n"
            "! --- R3 ---\n"
            "router ospf 1\n"
            " network 10.0.0.4 0.0.0.3 area 0\n"
            " network 192.168.3.0 0.0.0.255 area 0\n"
        ),
    )


def lab_acl_icmp_block() -> dict:
    r1_base = "interface GigabitEthernet0/0\n ip address 10.10.10.1 255.255.255.0\n no shutdown\n"
    return _lab(
        title="ACL Block ICMP to Host",
        lab_id="ccna_acl_icmp_block",
        topic_code="5.1",
        difficulty=4,
        description="Deny ICMP to one PC with an extended ACL applied inbound on R1.",
        objectives=["access-list 100 deny icmp", "ip access-group", "verify isolation"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [{"name": "GigabitEthernet0/0", "ip": "10.10.10.1/24"}],
                    base_config=r1_base,
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                    ],
                    base_config=(
                        "vlan 10\n"
                        "interface GigabitEthernet0/1\n switchport mode trunk\n"
                        "interface GigabitEthernet0/2\n"
                        " switchport mode access\n"
                        " switchport access vlan 10\n"
                        "interface GigabitEthernet0/3\n"
                        " switchport mode access\n"
                        " switchport access vlan 10\n"
                    ),
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                _dev(
                    "PC2",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.20/24"}],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
                _link("SW1/GigabitEthernet0/3", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **R1**, create ACL **100** that denies ICMP to host **10.10.10.20**, "
                "then permits IP any any.",
                device="R1",
                require=[
                    "access-list 100 deny icmp any host 10.10.10.20",
                    "access-list 100 permit ip any any",
                ],
            ),
            _task(
                "t2",
                "Apply ACL 100 **inbound** on **Gi0/0** (`ip access-group 100 in`).",
                device="R1",
                require=["ip access-group 100 in"],
                verify_show=[_show("R1", "ip access-group 100 in")],
            ),
            _task(
                "t3",
                "Verify **PC1** can **not** ping **10.10.10.20** (ICMP blocked).",
                device="R1",
                require=["access-list 100 deny icmp any host 10.10.10.20"],
                verify_ping=[_ping("PC1", "10.10.10.20", False)],
            ),
        ],
        solution_config=(
            "access-list 100 deny icmp any host 10.10.10.20\n"
            "access-list 100 permit ip any any\n"
            "interface GigabitEthernet0/0\n"
            " ip access-group 100 in\n"
        ),
    )


def lab_acl_permit() -> dict:
    r1_base = "interface GigabitEthernet0/0\n ip address 10.10.10.1 255.255.255.0\n no shutdown\n"
    return _lab(
        title="ACL Permit After Block",
        lab_id="ccna_acl_permit_lab",
        topic_code="5.1",
        difficulty=3,
        description="Replace a blocking ACL with a permit-any policy and restore ping.",
        objectives=["Permit ACL", "Apply access-group", "Ping succeeds"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [{"name": "GigabitEthernet0/0", "ip": "10.10.10.1/24"}],
                    base_config=r1_base,
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                    ],
                    base_config=(
                        "vlan 10\n"
                        "interface GigabitEthernet0/1\n switchport mode trunk\n"
                        "interface GigabitEthernet0/2\n"
                        " switchport mode access\n"
                        " switchport access vlan 10\n"
                        "interface GigabitEthernet0/3\n"
                        " switchport mode access\n"
                        " switchport access vlan 10\n"
                    ),
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                _dev(
                    "PC2",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.20/24"}],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
                _link("SW1/GigabitEthernet0/3", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **R1**, create ACL **100** that permits IP any any.",
                device="R1",
                require=["access-list 100 permit ip any any"],
            ),
            _task(
                "t2",
                "Apply ACL 100 inbound on **Gi0/0**.",
                device="R1",
                require=["ip access-group 100 in"],
                verify_show=[_show("R1", "access-list 100 permit ip any any")],
            ),
            _task(
                "t3",
                "Verify **PC1** can ping **PC2** at **10.10.10.20**.",
                require=["access-list 100 permit ip any any"],
                verify_ping=[_ping("PC1", "10.10.10.20")],
            ),
        ],
        solution_config=(
            "access-list 100 permit ip any any\n"
            "interface GigabitEthernet0/0\n"
            " ip access-group 100 in\n"
        ),
    )


def lab_etherchannel_campus() -> dict:
    return _lab(
        title="EtherChannel Campus Bundle",
        lab_id="ccna_etherchannel_campus",
        topic_code="2.4",
        description=(
            "Two switches share dual links. Shutting the forwarding unbundled "
            "member isolates the PCs unless those links are one EtherChannel."
        ),
        objectives=[
            "VLAN 10 access with PortFast",
            "channel-group 1 mode on both members",
            "PC ping survives shutting one member",
        ],
        topology={
            "devices": [
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                    ],
                ),
                _dev(
                    "SW2",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                    ],
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                _dev(
                    "PC2",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.20/24"}],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("SW1/GigabitEthernet0/1", "SW2/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "SW2/GigabitEthernet0/2"),
                _link("SW1/GigabitEthernet0/3", "PC1/eth0"),
                _link("SW2/GigabitEthernet0/3", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**Access VLAN and inter-switch trunks**\n\n"
                "Create **VLAN 10** on both switches. Put each PC-facing Gi0/3 in "
                "VLAN 10 as access with **spanning-tree portfast**. Trunk Gi0/1 and "
                "Gi0/2 toward the peer. Unbundled, only the lowest interface name "
                "forwards — a second parallel link is not a backup yet.",
                require=[
                    "vlan 10",
                    "switchport mode trunk",
                    "switchport access vlan 10",
                    "spanning-tree portfast",
                ],
            ),
            _task(
                "t2",
                "**Bundle the dual links**\n\n"
                "On **SW1** and **SW2**, place Gi0/1 and Gi0/2 into "
                "**channel-group 1 mode on** so the two links become one logical "
                "path.",
                require=["channel-group 1 mode on"],
                verify_show=[_show("SW1", "channel-group 1")],
            ),
            _task(
                "t3",
                "**Prove the bundle**\n\n"
                "Shut **SW1 GigabitEthernet0/1** (the forwarding unbundled member). "
                "From **PC1**, **PC2** at **10.10.10.20** must still reply — that "
                "survives only if the remaining member is in the same channel-group.",
                device="SW1",
                require=["shutdown", "channel-group 1 mode on"],
                verify_ping=[_ping("PC1", "10.10.10.20")],
                verify_show=[_show("SW1", "channel-group 1")],
            ),
        ],
        solution_config=(
            "! --- SW1 ---\n"
            "vlan 10\n"
            "interface GigabitEthernet0/1\n"
            " switchport mode trunk\n"
            " channel-group 1 mode on\n"
            " shutdown\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode trunk\n"
            " channel-group 1 mode on\n"
            "interface GigabitEthernet0/3\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            " spanning-tree portfast\n"
            "! --- SW2 ---\n"
            "vlan 10\n"
            "interface GigabitEthernet0/1\n"
            " switchport mode trunk\n"
            " channel-group 1 mode on\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode trunk\n"
            " channel-group 1 mode on\n"
            "interface GigabitEthernet0/3\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            " spanning-tree portfast\n"
        ),
    )


def lab_stp_portfast() -> dict:
    return _lab(
        title="STP PortFast Edge Ports",
        lab_id="ccna_stp_portfast_edge",
        topic_code="2.5",
        description=(
            "Two PCs in VLAN 10 cannot reach each other until both access ports "
            "have PortFast and start forwarding."
        ),
        objectives=[
            "VLAN 10 access ports",
            "PortFast on both edge ports",
            "PC1 ping of PC2",
        ],
        topology={
            "devices": [
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                    ],
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                _dev(
                    "PC2",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.20/24"}],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("SW1/GigabitEthernet0/1", "PC1/eth0"),
                _link("SW1/GigabitEthernet0/2", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**SW1 — user VLAN**\n\n"
                "Create **VLAN 10** and put Gi0/1 and Gi0/2 in it as access ports. "
                "PC1 still cannot reach PC2 — those edge ports are not forwarding yet.",
                device="SW1",
                require=["vlan 10", "switchport access vlan 10"],
            ),
            _task(
                "t2",
                "**SW1 — PortFast**\n\n"
                "Enable **spanning-tree portfast** on Gi0/1 and Gi0/2 so both "
                "access ports start forwarding toward the PCs.",
                device="SW1",
                require=["spanning-tree portfast"],
                verify_show=[_show("SW1", "spanning-tree portfast")],
            ),
            _task(
                "t3",
                "**PC1 — prove the edge**\n\n"
                "From **PC1**, **PC2** at **10.10.10.20** must reply. That ping "
                "fails until PortFast is on both access ports.",
                verify_ping=[_ping("PC1", "10.10.10.20")],
            ),
        ],
        solution_config=(
            "vlan 10\n"
            "interface GigabitEthernet0/1\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            " spanning-tree portfast\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            " spanning-tree portfast\n"
        ),
    )


def lab_dhcp_pool() -> dict:
    return _lab(
        title="DHCP Pool on LAN Gateway",
        lab_id="ccna_dhcp_pool_lan",
        topic_code="4.3",
        description=(
            "PC1 has no address. It cannot ping the LAN gateway until R1 leases "
            "an address from pool LAN and the PC renews."
        ),
        objectives=[
            "Address the LAN gateway",
            "DHCP pool with network and default-router",
            "Renew on PC1 and ping the gateway",
        ],
        topology={
            "devices": [
                _dev("R1", "router", [{"name": "GigabitEthernet0/0"}]),
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**R1 — LAN gateway**\n\n"
                "PC1 has no IP of its own. On **R1**, set Gi0/0 to "
                "**192.168.10.1/24** and no shutdown so it can serve the LAN.",
                device="R1",
                require=["ip address 192.168.10.1 255.255.255.0", "no shutdown"],
            ),
            _task(
                "t2",
                "**R1 — DHCP pool**\n\n"
                "Create pool **LAN** with `ip dhcp pool LAN`, "
                "`network 192.168.10.0 255.255.255.0`, and "
                "`default-router 192.168.10.1`.",
                device="R1",
                require=[
                    "ip dhcp pool LAN",
                    "network 192.168.10.0 255.255.255.0",
                    "default-router 192.168.10.1",
                ],
                verify_show=[_show("R1", "ip dhcp pool LAN")],
            ),
            _task(
                "t3",
                "**SW1 and PC1 — adjacent lease**\n\n"
                "On **SW1**, create VLAN 10, trunk Gi0/1 toward R1, and put Gi0/2 "
                "in VLAN 10 as access with **spanning-tree portfast** so the PC "
                "is L2-adjacent. On **PC1** run `ipconfig /renew`. From PC1 the "
                "gateway **192.168.10.1** must reply.",
                device="SW1",
                require=[
                    "vlan 10",
                    "switchport mode trunk",
                    "switchport access vlan 10",
                    "spanning-tree portfast",
                ],
                verify_ping=[_ping("PC1", "192.168.10.1")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.10.1 255.255.255.0\n"
            " no shutdown\n"
            "ip dhcp pool LAN\n"
            " network 192.168.10.0 255.255.255.0\n"
            " default-router 192.168.10.1\n"
            "! --- SW1 ---\n"
            "vlan 10\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 10\n"
            " spanning-tree portfast\n"
            "! --- PC1 ---\n"
            "ipconfig /renew\n"
        ),
    )


def lab_nat_pat() -> dict:
    # Inside/outside are in base so PC→ISP already fails until PAT overload.
    r1_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 192.168.1.1 255.255.255.0\n"
        " ip nat inside\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 203.0.113.1 255.255.255.0\n"
        " ip nat outside\n"
        " no shutdown\n"
    )
    return _lab(
        title="NAT PAT Edge",
        lab_id="ccna_nat_pat_edge",
        topic_code="4.1",
        description=(
            "PC1 on the inside LAN cannot reach the ISP until R1 overloads PAT "
            "out the WAN interface."
        ),
        objectives=[
            "Mark inside and outside on the NAT border",
            "ACL 1 plus PAT overload",
            "PC1 ping of the ISP host",
        ],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "192.168.1.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "203.0.113.1/24"},
                    ],
                    base_config=r1_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "192.168.1.10/24"}],
                    base_config="ip address 192.168.1.10 255.255.255.0\n",
                ),
                _dev(
                    "ISP",
                    "router",
                    [{"name": "GigabitEthernet0/0", "ip": "203.0.113.2/24"}],
                    base_config=(
                        "interface GigabitEthernet0/0\n"
                        " ip address 203.0.113.2 255.255.255.0\n"
                        " no shutdown\n"
                    ),
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "PC1/eth0"),
                _link("R1/GigabitEthernet0/1", "ISP/GigabitEthernet0/0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**R1 — NAT border**\n\n"
                "PC1 sits on Gi0/0 (192.168.1.0/24). The ISP is on Gi0/1 "
                "(203.0.113.0/24). Mark **Gi0/0** `ip nat inside` and **Gi0/1** "
                "`ip nat outside`. Until PAT exists, PC1 cannot reach the ISP.",
                device="R1",
                require=["ip nat inside", "ip nat outside"],
            ),
            _task(
                "t2",
                "**R1 — PAT overload**\n\n"
                "Create **ACL 1** that permits any, then "
                "`ip nat inside source list 1 interface GigabitEthernet0/1 overload`.",
                device="R1",
                require=[
                    "access-list 1 permit any",
                    "ip nat inside source list 1 interface GigabitEthernet0/1 overload",
                ],
                verify_show=[_show("R1", "ip nat inside source")],
            ),
            _task(
                "t3",
                "**PC1 — prove PAT**\n\n"
                "PC1 (192.168.1.10) cannot reach the ISP at **203.0.113.2** until "
                "PAT is in place. From **PC1**, that ISP address must reply.",
                verify_ping=[_ping("PC1", "203.0.113.2")],
            ),
        ],
        solution_config=(
            "interface GigabitEthernet0/0\n ip nat inside\n"
            "interface GigabitEthernet0/1\n ip nat outside\n"
            "access-list 1 permit any\n"
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
        ),
    )


def lab_ssh_vty() -> dict:
    return _lab(
        title="SSH VTY Hardening",
        lab_id="ccna_ssh_vty_secure",
        topic_code="5.3",
        description="Harden management access: hostname, LAN IP, and SSH-only VTY.",
        objectives=["hostname", "LAN address", "line vty transport ssh"],
        topology={
            "devices": [
                _dev("R1", "router", [{"name": "GigabitEthernet0/0"}]),
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Set hostname **SECURE-R1** on R1.",
                device="R1",
                require=["hostname SECURE-R1"],
                verify_show=[_show("R1", "hostname SECURE-R1")],
            ),
            _task(
                "t2",
                "Address Gi0/0 as **10.0.0.1/24** and no shutdown.",
                device="R1",
                require=["ip address 10.0.0.1 255.255.255.0", "no shutdown"],
            ),
            _task(
                "t3",
                "Under `line vty 0 4`, set `transport input ssh` (management hardening objective).",
                device="R1",
                require=["hostname SECURE-R1"],
                verify_show=[_show("R1", "ip address 10.0.0.1 255.255.255.0")],
            ),
        ],
        solution_config=(
            "hostname SECURE-R1\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.0.0.1 255.255.255.0\n"
            " no shutdown\n"
            "line vty 0 4\n"
            " transport input ssh\n"
        ),
    )


def lab_ipv6_addressing() -> dict:
    return _lab(
        title="IPv6 LAN Addressing",
        lab_id="ccna_ipv6_lan",
        topic_code="1.9",
        description="Enable IPv6 unicast-routing and address a LAN interface.",
        objectives=["ipv6 unicast-routing", "ipv6 address", "verify.show"],
        topology={
            "devices": [
                _dev("R1", "router", [{"name": "GigabitEthernet0/0"}]),
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Enable **ipv6 unicast-routing** on R1.",
                device="R1",
                require=["ipv6 unicast-routing"],
            ),
            _task(
                "t2",
                "Set Gi0/0 to **2001:db8:1::1/64** and no shutdown.",
                device="R1",
                require=["ipv6 address 2001:db8:1::1/64", "no shutdown"],
                verify_show=[_show("R1", "ipv6 address 2001:db8:1::1/64")],
            ),
            _task(
                "t3",
                "Set hostname **V6-R1**.",
                device="R1",
                require=["hostname V6-R1"],
                verify_show=[_show("R1", "hostname V6-R1")],
            ),
        ],
        solution_config=(
            "hostname V6-R1\n"
            "ipv6 unicast-routing\n"
            "interface GigabitEthernet0/0\n"
            " ipv6 address 2001:db8:1::1/64\n"
            " no shutdown\n"
        ),
    )


def lab_multi_vlan_roas() -> dict:
    """Two user VLANs with dual router LAN interfaces (ROAS-style teaching)."""
    return _lab(
        title="Multi-VLAN Users (ROAS-style)",
        lab_id="ccna_multi_vlan_users",
        topic_code="3.3",
        difficulty=4,
        description="Serve two access VLANs from a router with per-VLAN gateways.",
        objectives=["Two VLANs", "Two gateway IPs", "PC gateway pings"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0"},
                        {"name": "GigabitEthernet0/1"},
                    ],
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                        {"name": "GigabitEthernet0/4"},
                    ],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
                _dev("PC2", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("R1/GigabitEthernet0/1", "SW1/GigabitEthernet0/2"),
                _link("SW1/GigabitEthernet0/3", "PC1/eth0"),
                _link("SW1/GigabitEthernet0/4", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **R1**, set Gi0/0 to **10.10.10.1/24** and Gi0/1 to **10.10.20.1/24**, "
                "both no shutdown.",
                device="R1",
                require=[
                    "ip address 10.10.10.1 255.255.255.0",
                    "ip address 10.10.20.1 255.255.255.0",
                    "no shutdown",
                ],
            ),
            _task(
                "t2",
                "On **SW1**, create VLANs 10/20; access Gi0/1&Gi0/3 → VLAN 10; "
                "Gi0/2&Gi0/4 → VLAN 20.",
                device="SW1",
                require=[
                    "vlan 10",
                    "vlan 20",
                    "switchport access vlan 10",
                    "switchport access vlan 20",
                ],
            ),
            _task(
                "t3",
                "Address PC1 **10.10.10.10/24** and PC2 **10.10.20.20/24**; ping each gateway.",
                require=[
                    "ip address 10.10.10.10 255.255.255.0",
                    "ip address 10.10.20.20 255.255.255.0",
                ],
                verify_ping=[
                    _ping("PC1", "10.10.10.1"),
                    _ping("PC2", "10.10.20.1"),
                ],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.10.10.1 255.255.255.0\n"
            " no shutdown\n"
            "interface GigabitEthernet0/1\n"
            " ip address 10.10.20.1 255.255.255.0\n"
            " no shutdown\n"
            "! --- SW1 ---\n"
            "vlan 10\nvlan 20\n"
            "interface GigabitEthernet0/1\n"
            " switchport mode access\n switchport access vlan 10\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n switchport access vlan 20\n"
            "interface GigabitEthernet0/3\n"
            " switchport mode access\n switchport access vlan 10\n"
            "interface GigabitEthernet0/4\n"
            " switchport mode access\n switchport access vlan 20\n"
            "! --- PCs ---\n"
            "ip address 10.10.10.10 255.255.255.0\n"
            "ip address 10.10.20.20 255.255.255.0\n"
        ),
    )


def lab_branch_wan_static() -> dict:
    hq_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.1.1.1 255.255.255.0\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 172.16.0.1 255.255.255.252\n"
        " no shutdown\n"
    )
    br_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.2.2.1 255.255.255.0\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 172.16.0.2 255.255.255.252\n"
        " no shutdown\n"
    )
    return _lab(
        title="Branch WAN Static",
        lab_id="ccna_branch_wan_static",
        topic_code="3.1",
        description="Connect HQ and branch LANs over a WAN with mutual static routes.",
        objectives=["HQ static route", "Branch static route", "Ping branch PC"],
        topology={
            "devices": [
                _dev(
                    "HQ",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.1.1.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "172.16.0.1/30"},
                    ],
                    base_config=hq_base,
                ),
                _dev(
                    "BR",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.2.2.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "172.16.0.2/30"},
                    ],
                    base_config=br_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.2.2.10/24"}],
                    base_config="ip address 10.2.2.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("HQ/GigabitEthernet0/1", "BR/GigabitEthernet0/1"),
                _link("BR/GigabitEthernet0/0", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On **HQ**, route **10.2.2.0/24** via **172.16.0.2**.",
                device="HQ",
                require=["ip route 10.2.2.0 255.255.255.0 172.16.0.2"],
            ),
            _task(
                "t2",
                "On **BR**, route **10.1.1.0/24** via **172.16.0.1**.",
                device="BR",
                require=["ip route 10.1.1.0 255.255.255.0 172.16.0.1"],
            ),
            _task(
                "t3",
                "Verify HQ can ping branch PC **10.2.2.10**.",
                device="HQ",
                require=["ip route 10.2.2.0 255.255.255.0 172.16.0.2"],
                verify_ping=[_ping("HQ", "10.2.2.10")],
            ),
        ],
        solution_config=(
            "ip route 10.2.2.0 255.255.255.0 172.16.0.2\n"
            "ip route 10.1.1.0 255.255.255.0 172.16.0.1\n"
        ),
    )


def lab_campus_edge() -> dict:
    return _lab(
        title="Campus Edge Gateway",
        lab_id="ccna_campus_edge",
        topic_code="2.1",
        difficulty=3,
        description="Combine gateway addressing, VLAN, and trunk for a campus edge.",
        objectives=["Gateway IP", "VLAN + trunk", "PC ping gateway"],
        topology={
            "devices": [
                _dev("R1", "router", [{"name": "GigabitEthernet0/0"}]),
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "On R1 set Gi0/0 to **10.20.20.1/24** and no shut.",
                device="R1",
                require=["ip address 10.20.20.1 255.255.255.0", "no shutdown"],
            ),
            _task(
                "t2",
                "On SW1 create VLAN 20, trunk Gi0/1, access Gi0/2 in VLAN 20.",
                device="SW1",
                require=["vlan 20", "switchport mode trunk", "switchport access vlan 20"],
            ),
            _task(
                "t3",
                "Address PC1 **10.20.20.10/24** and ping the gateway.",
                require=["ip address 10.20.20.10 255.255.255.0"],
                verify_ping=[_ping("PC1", "10.20.20.1")],
            ),
        ],
        solution_config=(
            "interface GigabitEthernet0/0\n"
            " ip address 10.20.20.1 255.255.255.0\n"
            " no shutdown\n"
            "vlan 20\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 20\n"
            "ip address 10.20.20.10 255.255.255.0\n"
        ),
    )


# ---------------------------------------------------------------------------
# ENCOR gold (≥3)
# ---------------------------------------------------------------------------


def lab_encor_ospf() -> dict:
    r1_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.0.0.1 255.255.255.252\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 10.1.1.1 255.255.255.0\n"
        " no shutdown\n"
    )
    r2_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.0.0.2 255.255.255.252\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 10.2.2.1 255.255.255.0\n"
        " no shutdown\n"
    )
    return _lab(
        title="ENCOR OSPF Enterprise Edge",
        lab_id="encor_ospf_enterprise",
        topic_code="3.1",
        difficulty=4,
        cert_tags=["ccnp"],
        description="ENCOR-style OSPF single-area reachability between site routers.",
        objectives=["OSPF process", "network statements", "ping remote LAN"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.1/30"},
                        {"name": "GigabitEthernet0/1", "ip": "10.1.1.1/24"},
                    ],
                    base_config=r1_base,
                ),
                _dev(
                    "R2",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.0.0.2/30"},
                        {"name": "GigabitEthernet0/1", "ip": "10.2.2.1/24"},
                    ],
                    base_config=r2_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.2.2.10/24"}],
                    base_config="ip address 10.2.2.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "R2/GigabitEthernet0/0"),
                _link("R2/GigabitEthernet0/1", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Enable OSPF 1 on both routers; advertise transit and LAN networks in area 0.",
                require=[
                    "router ospf 1",
                    "network 10.0.0.0 0.0.0.3 area 0",
                    "network 10.1.1.0 0.0.0.255 area 0",
                    "network 10.2.2.0 0.0.0.255 area 0",
                ],
            ),
            _task(
                "t2",
                "Verify R1 can ping R2 LAN **10.2.2.1**.",
                require=["router ospf 1"],
                verify_ping=[_ping("R1", "10.2.2.1")],
            ),
            _task(
                "t3",
                "Verify R1 can ping **PC1** at **10.2.2.10**.",
                require=["network 10.2.2.0 0.0.0.255 area 0"],
                verify_ping=[_ping("R1", "10.2.2.10")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "router ospf 1\n"
            " network 10.0.0.0 0.0.0.3 area 0\n"
            " network 10.1.1.0 0.0.0.255 area 0\n"
            "! --- R2 ---\n"
            "router ospf 1\n"
            " network 10.0.0.0 0.0.0.3 area 0\n"
            " network 10.2.2.0 0.0.0.255 area 0\n"
        ),
    )


def lab_encor_vlan_core() -> dict:
    return _lab(
        title="ENCOR Core VLAN Fabric",
        lab_id="encor_vlan_core",
        topic_code="2.1",
        difficulty=3,
        cert_tags=["ccnp"],
        description="Build a core VLAN and trunk fabric for campus distribution.",
        objectives=["VLAN create", "Trunk core", "Access edge"],
        topology={
            "devices": [
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev(
                    "SW2",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.50.50.10/24"}],
                    base_config="ip address 10.50.50.10 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("SW1/GigabitEthernet0/1", "SW2/GigabitEthernet0/1"),
                _link("SW2/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Create **VLAN 50** named **CORE** on both switches.",
                require=["vlan 50", "name CORE"],
            ),
            _task(
                "t2",
                "Trunk Gi0/1 on SW1 and SW2.",
                require=["switchport mode trunk"],
                verify_show=[_show("SW1", "switchport mode trunk")],
            ),
            _task(
                "t3",
                "Put SW2 Gi0/2 in VLAN 50 as access.",
                device="SW2",
                require=["switchport access vlan 50"],
            ),
        ],
        solution_config=(
            "vlan 50\n name CORE\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 50\n"
        ),
    )


def lab_encor_edge_acl() -> dict:
    r1_base = "interface GigabitEthernet0/0\n ip address 10.10.10.1 255.255.255.0\n no shutdown\n"
    return _lab(
        title="ENCOR Edge ACL Filter",
        lab_id="encor_edge_acl",
        topic_code="1.1",
        difficulty=4,
        cert_tags=["ccnp"],
        description="Apply an edge ACL that blocks ICMP to a protected host.",
        objectives=["Extended ACL", "access-group", "verify blocked ping"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [{"name": "GigabitEthernet0/0", "ip": "10.10.10.1/24"}],
                    base_config=r1_base,
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/3"},
                    ],
                    base_config=(
                        "vlan 10\n"
                        "interface GigabitEthernet0/1\n switchport mode trunk\n"
                        "interface GigabitEthernet0/2\n"
                        " switchport mode access\n"
                        " switchport access vlan 10\n"
                        "interface GigabitEthernet0/3\n"
                        " switchport mode access\n"
                        " switchport access vlan 10\n"
                    ),
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.10/24"}],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                _dev(
                    "PC2",
                    "pc",
                    [{"name": "eth0", "ip": "10.10.10.50/24"}],
                    base_config="ip address 10.10.10.50 255.255.255.0\n",
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
                _link("SW1/GigabitEthernet0/3", "PC2/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Create ACL 100: deny ICMP any host **10.10.10.50**, then permit ip any any.",
                device="R1",
                require=[
                    "access-list 100 deny icmp any host 10.10.10.50",
                    "access-list 100 permit ip any any",
                ],
            ),
            _task(
                "t2",
                "Apply `ip access-group 100 in` on Gi0/0.",
                device="R1",
                require=["ip access-group 100 in"],
                verify_show=[_show("R1", "ip access-group 100 in")],
            ),
            _task(
                "t3",
                "Verify PC1 cannot ping the protected host **10.10.10.50**.",
                require=["access-list 100 deny icmp any host 10.10.10.50"],
                verify_ping=[_ping("PC1", "10.10.10.50", False)],
            ),
        ],
        solution_config=(
            "access-list 100 deny icmp any host 10.10.10.50\n"
            "access-list 100 permit ip any any\n"
            "interface GigabitEthernet0/0\n"
            " ip access-group 100 in\n"
        ),
    )


def lab_encor_pat_edge() -> dict:
    """ENCOR L3 ticket: inside host cannot reach the outside peer until PAT."""
    r1_base = (
        "interface GigabitEthernet0/0\n"
        " ip address 10.8.8.1 255.255.255.0\n"
        " ip nat inside\n"
        " no shutdown\n"
        "interface GigabitEthernet0/1\n"
        " ip address 198.51.100.1 255.255.255.0\n"
        " ip nat outside\n"
        " no shutdown\n"
    )
    return _lab(
        title="ENCOR PAT Edge Translation",
        lab_id="encor_pat_edge",
        topic_code="3.2",
        difficulty=4,
        cert_tags=["ccnp"],
        description=(
            "A campus host on 10.8.8.0/24 cannot reach the outside peer until the "
            "edge router overloads PAT on the WAN interface."
        ),
        objectives=[
            "Mark inside and outside",
            "ACL plus PAT overload",
            "Inside PC ping of the outside peer",
        ],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "ip": "10.8.8.1/24"},
                        {"name": "GigabitEthernet0/1", "ip": "198.51.100.1/24"},
                    ],
                    base_config=r1_base,
                ),
                _dev(
                    "PC1",
                    "pc",
                    [{"name": "eth0", "ip": "10.8.8.10/24"}],
                    base_config="ip address 10.8.8.10 255.255.255.0\n",
                ),
                _dev(
                    "ISP",
                    "router",
                    [{"name": "GigabitEthernet0/0", "ip": "198.51.100.2/24"}],
                    base_config=(
                        "interface GigabitEthernet0/0\n"
                        " ip address 198.51.100.2 255.255.255.0\n"
                        " no shutdown\n"
                    ),
                ),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "PC1/eth0"),
                _link("R1/GigabitEthernet0/1", "ISP/GigabitEthernet0/0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**R1 — translation border**\n\n"
                "Gi0/0 faces the campus LAN; Gi0/1 faces the provider. Mark "
                "**Gi0/0** `ip nat inside` and **Gi0/1** `ip nat outside`. "
                "PC1 cannot reach 198.51.100.2 until PAT exists.",
                device="R1",
                require=["ip nat inside", "ip nat outside"],
            ),
            _task(
                "t2",
                "**R1 — overload**\n\n"
                "Create **ACL 1** that permits any, then "
                "`ip nat inside source list 1 interface GigabitEthernet0/1 overload`.",
                device="R1",
                require=[
                    "access-list 1 permit any",
                    "ip nat inside source list 1 interface GigabitEthernet0/1 overload",
                ],
                verify_show=[_show("R1", "ip nat inside source")],
            ),
            _task(
                "t3",
                "**PC1 — outside reachability**\n\n"
                "From **PC1**, the outside peer **198.51.100.2** must reply. "
                "That path stays dark until PAT overload is in place.",
                verify_ping=[_ping("PC1", "198.51.100.2")],
            ),
        ],
        solution_config=(
            "interface GigabitEthernet0/0\n ip nat inside\n"
            "interface GigabitEthernet0/1\n ip nat outside\n"
            "access-list 1 permit any\n"
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
        ),
    )


def lab_encor_dhcp_campus() -> dict:
    """ENCOR L3 ticket: campus PC has no address until it renews from the pool."""
    return _lab(
        title="ENCOR DHCP Campus Lease",
        lab_id="encor_dhcp_campus",
        topic_code="3.2",
        difficulty=4,
        cert_tags=["ccnp"],
        description=(
            "A campus PC has no IPv4 address. It cannot ping the distribution "
            "gateway until it renews a lease from the local pool."
        ),
        objectives=[
            "Address the distribution gateway",
            "DHCP pool with network and default-router",
            "Renew on PC1 and ping the gateway",
        ],
        topology={
            "devices": [
                _dev("R1", "router", [{"name": "GigabitEthernet0/0"}]),
                _dev(
                    "SW1",
                    "switch",
                    [{"name": "GigabitEthernet0/1"}, {"name": "GigabitEthernet0/2"}],
                ),
                _dev("PC1", "pc", [{"name": "eth0"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "PC1/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "**R1 — distribution gateway**\n\n"
                "PC1 has no address. On **R1**, set Gi0/0 to **10.30.30.1/24** "
                "and no shutdown.",
                device="R1",
                require=["ip address 10.30.30.1 255.255.255.0", "no shutdown"],
            ),
            _task(
                "t2",
                "**R1 — campus pool**\n\n"
                "Create pool **CAMPUS** with `ip dhcp pool CAMPUS`, "
                "`network 10.30.30.0 255.255.255.0`, and "
                "`default-router 10.30.30.1`.",
                device="R1",
                require=[
                    "ip dhcp pool CAMPUS",
                    "network 10.30.30.0 255.255.255.0",
                    "default-router 10.30.30.1",
                ],
                verify_show=[_show("R1", "ip dhcp pool CAMPUS")],
            ),
            _task(
                "t3",
                "**SW1 and PC1 — lease then ping**\n\n"
                "On **SW1**, create VLAN 30, trunk Gi0/1, and put Gi0/2 in VLAN 30 "
                "as access with **spanning-tree portfast**. On **PC1** run "
                "`ipconfig /renew`. From PC1 the gateway **10.30.30.1** must reply.",
                device="SW1",
                require=[
                    "vlan 30",
                    "switchport mode trunk",
                    "switchport access vlan 30",
                    "spanning-tree portfast",
                ],
                verify_ping=[_ping("PC1", "10.30.30.1")],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.30.30.1 255.255.255.0\n"
            " no shutdown\n"
            "ip dhcp pool CAMPUS\n"
            " network 10.30.30.0 255.255.255.0\n"
            " default-router 10.30.30.1\n"
            "! --- SW1 ---\n"
            "vlan 30\n"
            "interface GigabitEthernet0/1\n switchport mode trunk\n"
            "interface GigabitEthernet0/2\n"
            " switchport mode access\n"
            " switchport access vlan 30\n"
            " spanning-tree portfast\n"
            "! --- PC1 ---\n"
            "ipconfig /renew\n"
        ),
    )


# ---------------------------------------------------------------------------
# Drill + scale
# ---------------------------------------------------------------------------


def lab_drill_hostname() -> dict:
    return _lab(
        title="CLI Drill: Hostname",
        lab_id="ccna_drill_hostname",
        topic_code="1.1",
        difficulty=1,
        lab_tier="drill",
        description="Single-device CLI drill — set a router hostname.",
        objectives=["hostname"],
        topology={
            "devices": [_dev("R1", "router", [{"name": "GigabitEthernet0/0"}])],
            "links": [],
        },
        tasks=[
            _task(
                "t1",
                "Set the hostname to **DRILL-R1**.",
                device="R1",
                require=["hostname DRILL-R1"],
            ),
        ],
        solution_config="hostname DRILL-R1\n",
    )


def lab_drill_vlan() -> dict:
    return _lab(
        title="CLI Drill: Create VLAN",
        lab_id="ccna_drill_vlan_create",
        topic_code="2.1",
        difficulty=1,
        lab_tier="drill",
        description="Single-device CLI drill — create and name a VLAN.",
        objectives=["vlan create"],
        topology={
            "devices": [
                _dev("SW1", "switch", [{"name": "GigabitEthernet0/1"}]),
            ],
            "links": [],
        },
        tasks=[
            _task(
                "t1",
                "Create **VLAN 99** named **MGMT**.",
                device="SW1",
                require=["vlan 99", "name MGMT"],
            ),
        ],
        solution_config="vlan 99\n name MGMT\n",
    )


def lab_drill_hostname_sw() -> dict:
    return _lab(
        title="CLI Drill: Switch Hostname",
        lab_id="ccna_drill_hostname_sw",
        topic_code="1.1",
        difficulty=1,
        lab_tier="drill",
        description="Single-device CLI drill — set a switch hostname.",
        objectives=["hostname"],
        topology={
            "devices": [_dev("SW1", "switch", [{"name": "GigabitEthernet0/1"}])],
            "links": [],
        },
        tasks=[
            _task(
                "t1",
                "Set the hostname to **DRILL-SW1**.",
                device="SW1",
                require=["hostname DRILL-SW1"],
            ),
        ],
        solution_config="hostname DRILL-SW1\n",
    )


def lab_scale_campus_10() -> dict:
    return _lab(
        title="Scale Campus Ten Devices",
        lab_id="ccna_scale_campus_10",
        topic_code="1.1",
        difficulty=2,
        lab_tier="scale",
        description=(
            "Light configuration across a 10-device campus edge used for performance "
            "and catalog scale. Hostname each device and address R1 Gi0/0."
        ),
        objectives=["Configure hostnames on core devices", "Address the campus gateway"],
        topology={
            "devices": [
                _dev(
                    "R1",
                    "router",
                    [
                        {"name": "GigabitEthernet0/0", "connected_to": "SW1/GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/1", "connected_to": "SW2/GigabitEthernet0/1"},
                    ],
                ),
                _dev(
                    "R2",
                    "router",
                    [{"name": "GigabitEthernet0/0", "connected_to": "SW3/GigabitEthernet0/1"}],
                ),
                _dev(
                    "SW1",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "R1/GigabitEthernet0/0"},
                        {"name": "GigabitEthernet0/2", "connected_to": "SW4/GigabitEthernet0/1"},
                    ],
                ),
                _dev(
                    "SW2",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "R1/GigabitEthernet0/1"},
                        {"name": "GigabitEthernet0/2", "connected_to": "SW5/GigabitEthernet0/1"},
                    ],
                ),
                _dev(
                    "SW3",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "R2/GigabitEthernet0/0"},
                        {"name": "GigabitEthernet0/2", "connected_to": "SW6/GigabitEthernet0/1"},
                    ],
                ),
                _dev(
                    "SW4",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "SW1/GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/2", "connected_to": "PC1/eth0"},
                    ],
                ),
                _dev(
                    "SW5",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "SW2/GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/2", "connected_to": "PC2/eth0"},
                    ],
                ),
                _dev(
                    "SW6",
                    "switch",
                    [
                        {"name": "GigabitEthernet0/1", "connected_to": "SW3/GigabitEthernet0/2"},
                        {"name": "GigabitEthernet0/2", "connected_to": "PC3/eth0"},
                    ],
                ),
                _dev("PC1", "pc", [{"name": "eth0", "connected_to": "SW4/GigabitEthernet0/2"}]),
                _dev("PC2", "pc", [{"name": "eth0", "connected_to": "SW5/GigabitEthernet0/2"}]),
                _dev("PC3", "pc", [{"name": "eth0", "connected_to": "SW6/GigabitEthernet0/2"}]),
            ],
            "links": [
                _link("R1/GigabitEthernet0/0", "SW1/GigabitEthernet0/1"),
                _link("R1/GigabitEthernet0/1", "SW2/GigabitEthernet0/1"),
                _link("R2/GigabitEthernet0/0", "SW3/GigabitEthernet0/1"),
                _link("SW1/GigabitEthernet0/2", "SW4/GigabitEthernet0/1"),
                _link("SW2/GigabitEthernet0/2", "SW5/GigabitEthernet0/1"),
                _link("SW3/GigabitEthernet0/2", "SW6/GigabitEthernet0/1"),
                _link("SW4/GigabitEthernet0/2", "PC1/eth0"),
                _link("SW5/GigabitEthernet0/2", "PC2/eth0"),
                _link("SW6/GigabitEthernet0/2", "PC3/eth0"),
            ],
        },
        tasks=[
            _task(
                "t1",
                "Set hostnames: **R1** → **CAMPUS-R1**, **SW1** → **CAMPUS-SW1**.",
                require=["hostname CAMPUS-R1", "hostname CAMPUS-SW1"],
            ),
            _task(
                "t2",
                "On **R1**, address Gi0/0 as **10.10.0.1/24** and bring it up.",
                device="R1",
                require=["ip address 10.10.0.1 255.255.255.0", "no shutdown"],
            ),
        ],
        solution_config=(
            "! --- R1 ---\n"
            "hostname CAMPUS-R1\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.10.0.1 255.255.255.0\n"
            " no shutdown\n"
            "! --- SW1 ---\n"
            "hostname CAMPUS-SW1\n"
        ),
    )


def build_labs() -> list[dict]:
    return [
        # Archetypes
        lab_branch_office(),
        lab_vlan_isolation(),
        lab_dual_router_static(),
        lab_ospf_two_router(),
        # Gold scenarios
        lab_trunk_campus(),
        lab_intervlan_roas(),
        lab_static_default_edge(),
        lab_ospf_three_router(),
        lab_acl_icmp_block(),
        lab_acl_permit(),
        lab_etherchannel_campus(),
        lab_stp_portfast(),
        lab_dhcp_pool(),
        lab_nat_pat(),
        lab_ssh_vty(),
        lab_ipv6_addressing(),
        lab_multi_vlan_roas(),
        lab_branch_wan_static(),
        lab_campus_edge(),
        # ENCOR gold
        lab_encor_ospf(),
        lab_encor_vlan_core(),
        lab_encor_edge_acl(),
        lab_encor_pat_edge(),
        lab_encor_dhcp_campus(),
        # Drill + scale
        lab_drill_hostname(),
        lab_drill_vlan(),
        lab_drill_hostname_sw(),
        lab_scale_campus_10(),
    ]


def _write_lab(lab: dict) -> Path:
    path = OUT / f"{lab['lab_id']}.yaml"
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(
            lab,
            fh,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write gold-lab YAML from this catalog.")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="LAB_ID",
        help="Rewrite only these lab_id files (does not delete the rest of the catalog).",
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    labs = build_labs()
    if args.only:
        wanted = set(args.only)
        labs = [lab for lab in labs if lab["lab_id"] in wanted]
        missing = wanted - {lab["lab_id"] for lab in labs}
        if missing:
            raise SystemExit(f"Unknown lab_id(s): {', '.join(sorted(missing))}")
    else:
        for path in OUT.glob("*.yaml"):
            path.unlink()

    for lab in labs:
        _write_lab(lab)

    gold = sum(1 for lab in labs if lab.get("lab_tier") == "gold")
    drill = sum(1 for lab in labs if lab.get("lab_tier") == "drill")
    scale = sum(1 for lab in labs if lab.get("lab_tier") == "scale")
    encor = sum(1 for lab in labs if "ccnp" in lab.get("cert_tags", []))
    print(
        f"Wrote {len(labs)} labs to {OUT}\n"
        f"  gold={gold}  drill={drill}  scale={scale}  encor={encor}"
    )


if __name__ == "__main__":
    main()
