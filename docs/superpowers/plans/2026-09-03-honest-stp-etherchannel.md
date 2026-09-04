# Honest STP PortFast and EtherChannel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. **Depends on:** NAT/DHCP tracks not required; can run after NAT. Do not simulate broadcast storms or PVST elections.

**Status: DONE** on `master` (`tests/netsim/test_stp_path.py`; unbundled dual
links block the redundant path; matching `channel-group` survives one shutdown).

**Boson gate:** PortFast and EtherChannel change forwarding used by ping.
Commands stuffed into `extra_lines` only is a fail. Depends on DHCP merge
(shared `device.py` / `world.py`).

**Goal:** A PC on a switch access port cannot ping until PortFast is enabled. Two parallel switch links without a matching channel-group are independent; with the same `channel-group`, they are one logical link so ping survives shutting one member.

**Architecture:** Typed flags on `InterfaceState`: `portfast: bool`, `channel_group: int | None`, `stp_forwarding: bool`. `LabWorld._l2_adjacent_or_same` / `_direct_link_up` consult forwarding state. Default: switch access ports facing PCs start `stp_forwarding=False` until `spanning-tree portfast`. Trunk and router-facing ports start forwarding (YAGNI). EtherChannel: `_direct_link_up` is true if **any** member of the same group is up, or if a non-bundled individual link is up.

**Tech Stack:** Python 3.11+, pytest, OpenIOS switch shell + world.

---

### Task 1: PortFast required for PC ping

**Files:**
- Create: `tests/netsim/test_stp_path.py`
- Modify: `src/openboson/netsim/ios/device.py`, `shell.py`, `world.py`

- [ ] **Step 1: Write failing tests**

```python
"""PortFast and EtherChannel must affect L2 forwarding used by ping."""

from __future__ import annotations

from openboson.netsim.ios.world import LabWorld
from openboson.netsim.lab_schema import (
    Device,
    DeviceType,
    Interface,
    LabBank,
    LabTask,
    LabTier,
    Link,
    Topology,
)


def _stp_lab() -> LabBank:
    return LabBank(
        title="STP path",
        lab_id="test_stp_path",
        topic_code="2.5",
        lab_tier=LabTier.DRILL,
        topology=Topology(
            devices=[
                Device(
                    name="SW1",
                    type=DeviceType.SWITCH,
                    interfaces=[
                        Interface(name="GigabitEthernet0/1"),
                        Interface(name="GigabitEthernet0/2"),
                    ],
                ),
                Device(
                    name="PC1",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="10.10.10.10/24")],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                Device(
                    name="PC2",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="10.10.10.20/24")],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            links=[
                Link(a="SW1/GigabitEthernet0/1", b="PC1/eth0"),
                Link(a="SW1/GigabitEthernet0/2", b="PC2/eth0"),
            ],
        ),
        tasks=[LabTask(id="t1", instructions="STP")],
    )


def _apply_pc_addrs(world: LabWorld, lab: LabBank) -> None:
    for d in lab.topology.devices:
        if d.type != DeviceType.PC:
            continue
        for line in (d.base_config or "").splitlines():
            if line.strip():
                world.shell(d.name).feed(line.strip())


def test_pc_ping_fails_until_portfast():
    lab = _stp_lab()
    world = LabWorld.from_lab(lab)
    _apply_pc_addrs(world, lab)
    sw = world.shell("SW1")
    for line in (
        "enable",
        "configure terminal",
        "vlan 10",
        "exit",
        "interface GigabitEthernet0/1",
        "switchport mode access",
        "switchport access vlan 10",
        "no shutdown",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 10",
        "no shutdown",
        "end",
    ):
        sw.feed(line)
    assert "0 percent" in world.ping("PC1", "10.10.10.20")
    sw.feed("enable")
    sw.feed("configure terminal")
    sw.feed("interface GigabitEthernet0/1")
    sw.feed("spanning-tree portfast")
    sw.feed("interface GigabitEthernet0/2")
    sw.feed("spanning-tree portfast")
    sw.feed("end")
    assert "100 percent" in world.ping("PC1", "10.10.10.20")
```

- [ ] **Step 2: Run** `python -m pytest tests/netsim/test_stp_path.py::test_pc_ping_fails_until_portfast -v`

Expected: FAIL — ping already 100% without PortFast.

- [ ] **Step 3: Implement**

`InterfaceState.portfast: bool = False` and `stp_forwarding: bool = True` (routers/PCs stay True).

When a switchport is set to `access`, set `stp_forwarding = False` until `portfast` is True. `_cmd_spanning_tree` sets `portfast = True` and `stp_forwarding = True` (and still renders `spanning-tree portfast`).

In `_direct_link_up`, require `ia.stp_forwarding and ib.stp_forwarding` in addition to admin/protocol up. PC interfaces always forwarding.

- [ ] **Step 4: Run test — PASS. Commit.**

```bash
git commit -m "Require PortFast on access ports before PC-to-PC ping."
```

---

### Task 2: EtherChannel logical link

**Files:**
- Modify: `tests/netsim/test_stp_path.py`, `device.py`, `shell.py`, `world.py`

- [ ] **Step 1: Write failing test**

Topology: SW1–SW2 with **two** links (Gi0/1–Gi0/1 and Gi0/2–Gi0/2), PC1 on SW1 Gi0/3, PC2 on SW2 Gi0/3, VLAN 10 access, PortFast on PC-facing ports.

```python
def _ec_lab() -> LabBank:
    return LabBank(
        title="EC path",
        lab_id="test_ec_path",
        topic_code="2.4",
        lab_tier=LabTier.DRILL,
        topology=Topology(
            devices=[
                Device(
                    name="SW1",
                    type=DeviceType.SWITCH,
                    interfaces=[
                        Interface(name="GigabitEthernet0/1"),
                        Interface(name="GigabitEthernet0/2"),
                        Interface(name="GigabitEthernet0/3"),
                    ],
                ),
                Device(
                    name="SW2",
                    type=DeviceType.SWITCH,
                    interfaces=[
                        Interface(name="GigabitEthernet0/1"),
                        Interface(name="GigabitEthernet0/2"),
                        Interface(name="GigabitEthernet0/3"),
                    ],
                ),
                Device(
                    name="PC1",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="10.10.10.10/24")],
                    base_config="ip address 10.10.10.10 255.255.255.0\n",
                ),
                Device(
                    name="PC2",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="10.10.10.20/24")],
                    base_config="ip address 10.10.10.20 255.255.255.0\n",
                ),
            ],
            links=[
                Link(a="SW1/GigabitEthernet0/1", b="SW2/GigabitEthernet0/1"),
                Link(a="SW1/GigabitEthernet0/2", b="SW2/GigabitEthernet0/2"),
                Link(a="SW1/GigabitEthernet0/3", b="PC1/eth0"),
                Link(a="SW2/GigabitEthernet0/3", b="PC2/eth0"),
            ],
        ),
        tasks=[LabTask(id="t1", instructions="EC")],
    )


def _prep_access_and_portfast(world: LabWorld) -> None:
    for sw in ("SW1", "SW2"):
        sh = world.shell(sw)
        for line in (
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
        ):
            sh.feed(line)


def test_etherchannel_keeps_ping_when_one_member_is_shut():
    lab = _ec_lab()
    world = LabWorld.from_lab(lab)
    _apply_pc_addrs(world, lab)
    _prep_access_and_portfast(world)
    for sw in ("SW1", "SW2"):
        sh = world.shell(sw)
        sh.feed("enable")
        sh.feed("configure terminal")
        sh.feed("interface GigabitEthernet0/1")
        sh.feed("channel-group 1 mode on")
        sh.feed("interface GigabitEthernet0/2")
        sh.feed("channel-group 1 mode on")
        sh.feed("end")
    world.shell("SW1").feed("enable")
    world.shell("SW1").feed("configure terminal")
    world.shell("SW1").feed("interface GigabitEthernet0/1")
    world.shell("SW1").feed("shutdown")
    world.shell("SW1").feed("end")
    assert "100 percent" in world.ping("PC1", "10.10.10.20")
```

Implement `_channel_up(a, b)`: true when there exists group G such that each switch has ≥1 interface in G that is admin_up, protocol_up, and stp_forwarding. `_l2_adjacent_or_same` for two switches uses `_channel_up` OR a single `_direct_link_up`.

- [ ] **Step 2: Parse** `_cmd_channel_group` already writes extra_lines; also set `iface.channel_group = group`.

- [ ] **Step 3: Tests PASS. Commit.**

```bash
git commit -m "Treat matching channel-group members as one logical L2 link."
```

---

### Task 3: Docs + exit

- [ ] Update `docs/openios-command-matrix.md` STP and EtherChannel rows with packet effects.
- [ ] Run `python -m pytest tests/netsim tests/gui/test_lab_flow.py -q`
- [ ] Next: `2026-09-03-gold-lab-tickets.md`
