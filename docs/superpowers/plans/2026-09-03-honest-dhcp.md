# Honest DHCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on:** `2026-09-03-honest-nat-path.md` merged or at least PC default-gateway forwarding.

**Goal:** A PC with no address cannot ping; after `ip dhcp pool` + `ipconfig /renew` it gets an address from the pool and can ping the gateway.

**Architecture:** Structured `DhcpPool` on `DeviceRuntime` parsed from `ip dhcp pool`, `network`, `default-router`, `ip dhcp excluded-address`. HostShell gains `ipconfig /renew` which asks the L2-adjacent router for a lease. `LabWorld.ping` already fails when the source has no IP (`_primary_ip` / connected subnets empty). Do not model DHCP relay or multiple pools per router in this slice.

**Tech Stack:** Python 3.11+, pytest, OpenIOS host + world.

---

### Task 1: Failing tests for empty PC and renew

**Files:**
- Create: `tests/netsim/test_dhcp_path.py`

- [ ] **Step 1: Write the failing tests**

```python
"""DHCP pool must assign a PC address before ping works."""

from __future__ import annotations

from openboson.netsim.ios.device import DeviceRole
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


def _dhcp_lab() -> LabBank:
    return LabBank(
        title="DHCP path",
        lab_id="test_dhcp_path",
        topic_code="4.3",
        lab_tier=LabTier.DRILL,
        topology=Topology(
            devices=[
                Device(
                    name="R1",
                    type=DeviceType.ROUTER,
                    interfaces=[Interface(name="GigabitEthernet0/0")],
                ),
                Device(
                    name="PC1",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0")],
                ),
            ],
            links=[Link(a="R1/GigabitEthernet0/0", b="PC1/eth0")],
        ),
        tasks=[LabTask(id="t1", instructions="DHCP")],
    )


def _prep_router(world: LabWorld) -> None:
    r1 = world.shell("R1")
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 192.168.10.1 255.255.255.0",
        "no shutdown",
        "exit",
        "ip dhcp pool LAN",
        "network 192.168.10.0 255.255.255.0",
        "default-router 192.168.10.1",
        "exit",
        "ip dhcp excluded-address 192.168.10.1 192.168.10.10",
        "end",
    ):
        r1.feed(line)


def test_pc_without_address_cannot_ping_gateway():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    _prep_router(world)
    result = world.ping("PC1", "192.168.10.1")
    assert "0 percent" in result


def test_ipconfig_renew_assigns_pool_address_and_ping_works():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    _prep_router(world)
    out = world.shell("PC1").feed("ipconfig /renew")
    text = out.output if hasattr(out, "output") else str(out)
    iface = world.devices["PC1"].interfaces["eth0"]
    assert iface.ip is not None
    assert iface.ip.startswith("192.168.10.")
    assert iface.ip != "192.168.10.1"
    # excluded 1–10, so first assignable is .11
    assert iface.ip == "192.168.10.11"
    result = world.ping("PC1", "192.168.10.1")
    assert "100 percent" in result
    assert "192.168.10.11" in text or "renew" in text.lower() or iface.ip in text


def test_renew_without_pool_leaves_pc_unaddressed():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    r1 = world.shell("R1")
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 192.168.10.1 255.255.255.0",
        "no shutdown",
        "end",
    ):
        r1.feed(line)
    world.shell("PC1").feed("ipconfig /renew")
    assert world.devices["PC1"].interfaces["eth0"].ip is None
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/netsim/test_dhcp_path.py -v`

Expected: `test_pc_without_address_cannot_ping_gateway` may PASS already (no IP). `test_ipconfig_renew_assigns_pool_address_and_ping_works` FAIL (`ipconfig /renew` unknown or no assignment).

- [ ] **Step 3: Commit tests**

```bash
git add tests/netsim/test_dhcp_path.py
git commit -m "Add DHCP path tests for pool assignment and ping."
```

---

### Task 2: Structured DHCP pool + parser

**Files:**
- Modify: `src/openboson/netsim/ios/device.py`
- Modify: `src/openboson/netsim/ios/shell.py` (`_cmd_ip_global`, config-dhcp mode or inline)

- [ ] **Step 1: Add types**

```python
@dataclass
class DhcpPool:
    name: str
    network: str | None = None
    mask: str | None = None
    default_router: str | None = None
    excluded: list[tuple[str, str]] = field(default_factory=list)
```

On `DeviceRuntime`:

```python
dhcp_pools: dict[str, DhcpPool] = field(default_factory=dict)
```

- [ ] **Step 2: Parse**

`ip dhcp pool LAN` enters a pool context (add `Mode.CONFIG_DHCP` or stash `_dhcp_pool_ctx` on the shell like `_vlan_ctx`).

Under that context:

- `network 192.168.10.0 255.255.255.0` sets network/mask
- `default-router 192.168.10.1` sets default_router
- `exit` returns to CONFIG

Global: `ip dhcp excluded-address 192.168.10.1 192.168.10.10` appends to **all pools on this device** for this slice (YAGNI: one pool).

Render in `running_config()`:

```
ip dhcp excluded-address 192.168.10.1 192.168.10.10
ip dhcp pool LAN
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.1
```

- [ ] **Step 3: Unit-level parse test** (add to `test_dhcp_path.py`)

```python
def test_dhcp_pool_renders_in_running_config():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    _prep_router(world)
    cfg = world.devices["R1"].running_config().lower()
    assert "ip dhcp pool lan" in cfg
    assert "network 192.168.10.0 255.255.255.0" in cfg
    assert "default-router 192.168.10.1" in cfg
```

- [ ] **Step 4: Run**

Run: `python -m pytest tests/netsim/test_dhcp_path.py::test_dhcp_pool_renders_in_running_config -v`

Expected: PASS after parser exists.

- [ ] **Step 5: Commit**

```bash
git add src/openboson/netsim/ios/device.py src/openboson/netsim/ios/shell.py tests/netsim/test_dhcp_path.py
git commit -m "Parse IOS DHCP pools into structured device state."
```

---

### Task 3: `ipconfig /renew` lease

**Files:**
- Modify: `src/openboson/netsim/ios/host.py`
- Modify: `src/openboson/netsim/ios/world.py` (`offer_dhcp` method)

- [ ] **Step 1: Implement `LabWorld.offer_dhcp(pc_name: str) -> str | None`**

Walk L2-adjacent routers. For each `DhcpPool` with network+mask:

- Build IPv4Network
- Collect used IPs: all device iface IPs + previous leases (store `dhcp_leases: dict[str, str]` PC→IP on the router, or on the world)
- Skip network, broadcast, excluded inclusive range, default-router
- First free host → assign to PC primary iface, set mask, `admin_up`, `default_gateway` from pool, refresh links
- Return the IP string

- [ ] **Step 2: HostShell**

In `feed`, if `cmd == "ipconfig"` and any arg in `{/renew, renew}`:

```python
if self.world is not None and hasattr(self.world, "offer_dhcp"):
    ip = self.world.offer_dhcp(self.device.name)
    if not ip:
        return ShellResult(output="DHCP lookup failed: no server or empty pool.")
    return ShellResult(output=f"Lease obtained: {ip}")
```

Also set `DHCP Enabled : Yes` in `_ipconfig` `/all` when `iface.ip` came from DHCP (`iface.dhcp_leased: bool = False` on InterfaceState).

- [ ] **Step 3: Run**

Run: `python -m pytest tests/netsim/test_dhcp_path.py -v`

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add src/openboson/netsim/ios/host.py src/openboson/netsim/ios/world.py src/openboson/netsim/ios/device.py tests/netsim/test_dhcp_path.py
git commit -m "Assign DHCP pool addresses on ipconfig /renew."
```

---

### Task 4: Docs + exit

- [ ] **Step 1:** Update `docs/openios-command-matrix.md` DHCP row: pool + excluded + host `ipconfig /renew` actually assign addresses used by ping.

- [ ] **Step 2:** Run `python -m pytest tests/netsim tests/gui/test_lab_flow.py -q` — all PASS

- [ ] **Step 3:** Commit docs. Next plan: `2026-09-03-honest-stp-etherchannel.md`.
