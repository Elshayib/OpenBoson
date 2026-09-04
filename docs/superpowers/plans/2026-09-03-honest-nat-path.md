# Honest NAT Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** **DONE** (shipped on master). `tests/netsim/test_nat_path.py` and
`LabWorld._nat_blocks_inside_to_outside` implement this. Do not re-run unless
those tests regress.

**Boson gate:** Inside-to-outside ICMP fails without PAT — NetSim-honest for this slice.

**Goal:** An inside PC cannot ping an outside peer until PAT overload is configured; with inside/outside + overload, ping succeeds.

**Architecture:** Give `InterfaceState` a `nat_role` and `DeviceRuntime` a structured `nat_overload`. Parse `ip nat …` in the shell into that state (running-config still renders the same lines). In `LabWorld._can_reach`, after ACL, require NAT when a packet leaves an inside interface toward an address owned on an outside interface’s subnet. PCs reach off-subnet destinations via their default gateway (`.1` convention already in `HostShell._guess_gateway`). Do not evaluate the NAT ACL contents in this slice.

**Tech Stack:** Python 3.11+, pytest, OpenIOS `LabWorld` / `OpenIOSShell` / `HostShell`.

---

### Task 1: Failing test — inside host cannot ping outside without PAT

**Files:**
- Create: `tests/netsim/test_nat_path.py`

- [ ] **Step 1: Write the failing test**

```python
"""NAT overload must be required for inside-host to outside-peer ping."""

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


def _nat_lab() -> LabBank:
    return LabBank(
        title="NAT path",
        lab_id="test_nat_path",
        topic_code="4.1",
        lab_tier=LabTier.DRILL,
        topology=Topology(
            devices=[
                Device(
                    name="R1",
                    type=DeviceType.ROUTER,
                    interfaces=[
                        Interface(name="GigabitEthernet0/0", ip="192.168.1.1/24"),
                        Interface(name="GigabitEthernet0/1", ip="203.0.113.1/24"),
                    ],
                    base_config=(
                        "interface GigabitEthernet0/0\n"
                        " ip address 192.168.1.1 255.255.255.0\n"
                        " no shutdown\n"
                        "interface GigabitEthernet0/1\n"
                        " ip address 203.0.113.1 255.255.255.0\n"
                        " no shutdown\n"
                    ),
                ),
                Device(
                    name="PC1",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="192.168.1.10/24")],
                    base_config="ip address 192.168.1.10 255.255.255.0\n",
                ),
                Device(
                    name="ISP",
                    type=DeviceType.ROUTER,
                    interfaces=[Interface(name="GigabitEthernet0/0", ip="203.0.113.2/24")],
                    base_config=(
                        "interface GigabitEthernet0/0\n"
                        " ip address 203.0.113.2 255.255.255.0\n"
                        " no shutdown\n"
                    ),
                ),
            ],
            links=[
                Link(a="R1/GigabitEthernet0/0", b="PC1/eth0"),
                Link(a="R1/GigabitEthernet0/1", b="ISP/GigabitEthernet0/0"),
            ],
        ),
        tasks=[LabTask(id="t1", instructions="NAT")],
    )


def _apply_base(world: LabWorld, lab: LabBank) -> None:
    for d in lab.topology.devices:
        cfg = (d.base_config or "").strip()
        if not cfg:
            continue
        shell = world.shell(d.name)
        from openboson.netsim.ios.device import DeviceRole

        runtime = world.devices[d.name]
        lines = [
            raw.strip()
            for raw in cfg.splitlines()
            if raw.strip() and not raw.strip().startswith("!")
        ]
        if runtime.role == DeviceRole.PC:
            for line in lines:
                shell.feed(line)
        else:
            shell.feed("enable")
            shell.feed("configure terminal")
            for line in lines:
                shell.feed(line)
            shell.feed("end")


def test_inside_host_cannot_ping_outside_without_pat():
    lab = _nat_lab()
    world = LabWorld.from_lab(lab)
    _apply_base(world, lab)
    result = world.ping("PC1", "203.0.113.2")
    assert "0 percent" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/netsim/test_nat_path.py::test_inside_host_cannot_ping_outside_without_pat -v`

Expected: FAIL with `assert "0 percent" in result` because `_can_reach` currently has no return-path/NAT gate (it may already fail for a different reason — no PC default route). Read the assertion. If ping already contains `0 percent`, the test **passes for the wrong reason**. In that case go to Task 2 first (default gateway), then re-run this test; it must fail only after off-net forwarding works without NAT.

- [ ] **Step 3: Do not implement NAT yet** if this test already fails due to missing default-gateway. Leave the test in place.

- [ ] **Step 4: Commit the test file**

```bash
git add tests/netsim/test_nat_path.py
git commit -m "Add NAT path test that inside hosts cannot reach outside without PAT."
```

---

### Task 2: PC default gateway for off-subnet ping

**Files:**
- Modify: `src/openboson/netsim/ios/host.py` (`_guess_gateway`, `_ip`)
- Modify: `src/openboson/netsim/ios/device.py` (`DeviceRuntime` — optional `default_gateway: str | None = None`)
- Modify: `src/openboson/netsim/ios/world.py` (`_can_reach`)
- Test: `tests/netsim/test_nat_path.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pc_reaches_connected_isp_peer_on_router_without_nat_is_still_defined():
    """Off-subnet ping uses the PC default gateway onto R1; NAT is a later gate."""
    lab = _nat_lab()
    world = LabWorld.from_lab(lab)
    _apply_base(world, lab)
    # Same subnet still works.
    result = world.ping("PC1", "192.168.1.1")
    assert "100 percent" in result
```

This one should already pass (connected subnet). Then add:

```python
def test_pc_off_subnet_uses_default_gateway():
    lab = _nat_lab()
    world = LabWorld.from_lab(lab)
    _apply_base(world, lab)
    # After default-gateway forwarding exists, this reaches R1 then ISP
    # unless NAT blocks it. We only assert the gateway IP is known on the PC.
    from openboson.netsim.ios.host import HostShell

    shell = world.shell("PC1")
    assert isinstance(shell, HostShell)
    assert shell._guess_gateway() == "192.168.1.1"
```

- [ ] **Step 2: Implement PC default-gateway as a route in `_can_reach`**

In `device.py` on `DeviceRuntime`:

```python
default_gateway: str | None = None
```

In `host.py` `_ip` after setting address:

```python
self.device.default_gateway = self._guess_gateway()
```

Also set it in `HostShell.__post_init__` / after base `ip address` feed.

In `world.py` `_can_reach`, after the connected-subnet loop, before `_routed`:

```python
if src.role == DeviceRole.PC and src.default_gateway:
    try:
        gw = IPv4Address(src.default_gateway)
    except ValueError:
        gw = None
    if gw is not None:
        gw_owner = self._owner_of_ip(gw)
        if gw_owner and self._l2_adjacent_or_same(from_device, gw_owner):
            return self._can_reach_via_router(gw_owner, from_device, dst)
```

Add `_can_reach_via_router(router, original_src, dst)` that:

1. Checks the router can reach `dst` with existing `_can_reach_simple` / connected / routed logic.
2. Calls `_nat_blocks_inside_to_outside(router, original_src, dst)` (Task 3 — for now return `False` so off-net ping **succeeds** without NAT).

If `_can_reach_simple` does not exist as a public path, reuse the connected + `_follow_routes` body used by `_can_reach` but **skip** the PC gateway recursion (depth guard).

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/netsim/test_nat_path.py -v`

Expected: `test_pc_off_subnet_uses_default_gateway` PASS. `test_inside_host_cannot_ping_outside_without_pat` should now **FAIL** (`100 percent` vs expected `0 percent`) if NAT is not yet blocking. That is the correct red for Task 3.

- [ ] **Step 4: Commit**

```bash
git add src/openboson/netsim/ios/device.py src/openboson/netsim/ios/host.py src/openboson/netsim/ios/world.py tests/netsim/test_nat_path.py
git commit -m "Route PC off-subnet pings through the default gateway."
```

---

### Task 3: NAT gate on inside-to-outside forwarding

**Files:**
- Modify: `src/openboson/netsim/ios/device.py`
- Modify: `src/openboson/netsim/ios/shell.py` (`_cmd_ip_if`, `_cmd_ip_global`)
- Modify: `src/openboson/netsim/ios/world.py`
- Test: `tests/netsim/test_nat_path.py`

- [ ] **Step 1: Write the passing-path test (will fail until parse + gate exist)**

```python
def _apply_pat(world: LabWorld) -> None:
    r1 = world.shell("R1")
    for line in (
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
    ):
        r1.feed(line)


def test_inside_host_pings_outside_with_pat():
    lab = _nat_lab()
    world = LabWorld.from_lab(lab)
    _apply_base(world, lab)
    _apply_pat(world)
    result = world.ping("PC1", "203.0.113.2")
    assert "100 percent" in result


def test_nat_inside_outside_render_in_running_config():
    lab = _nat_lab()
    world = LabWorld.from_lab(lab)
    _apply_base(world, lab)
    _apply_pat(world)
    cfg = world.devices["R1"].running_config().lower()
    assert "ip nat inside" in cfg
    assert "ip nat outside" in cfg
    assert "ip nat inside source list 1 interface gigabitethernet0/1 overload" in cfg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/netsim/test_nat_path.py::test_inside_host_pings_outside_with_pat tests/netsim/test_nat_path.py::test_inside_host_cannot_ping_outside_without_pat -v`

Expected: without-PAT still wrong or red from Task 2; with-PAT FAIL until gate + parse exist.

- [ ] **Step 3: Add typed state**

In `InterfaceState`:

```python
nat_role: str | None = None  # "inside" | "outside"
```

In `device.py` next to `StaticRoute`:

```python
@dataclass
class NatOverload:
    acl_id: str
    outside_iface: str
```

On `DeviceRuntime`:

```python
nat_overload: NatOverload | None = None
```

In `running_config()`, after interface IP lines, if `iface.nat_role`:

```python
lines.append(f" ip nat {iface.nat_role}")
```

Do **not** also keep a duplicate `ip nat inside` in `extra_lines` (pick one). Global overload: if `nat_overload` is set, render

```python
lines.append(
    f"ip nat inside source list {self.nat_overload.acl_id} "
    f"interface {self.nat_overload.outside_iface} overload"
)
```

before `extra_global` (and skip a matching extra_global line if present).

- [ ] **Step 4: Parse in the shell**

In `_cmd_ip_if`, before address handling:

```python
if args[0].lower() == "nat":
    iface = self._require_if()
    if len(args) < 2 or args[1].lower() not in {"inside", "outside"}:
        raise _CmdError("% Incomplete command.")
    iface.nat_role = args[1].lower()
    return ""
```

In `_cmd_ip_global`, replace the `args[0].lower() == "nat"` extra_global append with:

```python
if args[0].lower() == "nat":
    # ip nat inside source list 1 interface GigabitEthernet0/1 overload
    joined = [a.lower() for a in args]
    if (
        len(args) >= 7
        and joined[1] == "inside"
        and joined[2] == "source"
        and joined[3] == "list"
        and joined[5] == "interface"
    ):
        from openboson.netsim.ios.device import NatOverload

        outside = args[6]
        resolved = self.device.resolve_if_name(outside) or outside
        self.device.nat_overload = NatOverload(acl_id=args[4], outside_iface=resolved)
        return ""
    self.device.extra_global.append("ip " + " ".join(args))
    return ""
```

- [ ] **Step 5: Enforce the gate in `world.py`**

```python
def _nat_blocks_inside_to_outside(
    self, router: str, original_src: str, dst: IPv4Address
) -> bool:
    """True when this forwarding hop needs PAT and does not have it."""
    dev = self.devices[router]
    owner = self._owner_of_ip(dst)
    if owner is None:
        return False
    inside_ifaces = [i for i in dev.interfaces.values() if i.nat_role == "inside"]
    outside_ifaces = [i for i in dev.interfaces.values() if i.nat_role == "outside"]
    if not inside_ifaces and not outside_ifaces and dev.nat_overload is None:
        # No NAT config at all: still block RFC1918 source to a dst owned
        # on a different L3 interface of this router (typical edge PAT lab).
        src_ip = self._primary_ip(original_src)
        if src_ip is None or not src_ip.is_private:
            return False
        if self._l2_adjacent_or_same(original_src, owner):
            return False
        # Crossing this router from a private host to another interface's owner.
        if owner == router:
            return False
        return True
    src_on_inside = any(
        self._iface_faces_device(router, i.name, original_src) for i in inside_ifaces
    )
    dst_on_outside = any(
        self._iface_faces_device(router, i.name, owner) for i in outside_ifaces
    )
    if src_on_inside and dst_on_outside:
        return dev.nat_overload is None
    return False
```

Helper:

```python
def _iface_faces_device(self, router: str, ifname: str, peer: str) -> bool:
    for a_dev, a_if, b_dev, b_if in self.links:
        if a_dev == router and a_if == ifname and b_dev == peer:
            return True
        if b_dev == router and b_if == ifname and a_dev == peer:
            return True
    return False
```

Call `_nat_blocks_inside_to_outside` from `_can_reach_via_router`. If True, return False.

**No-NAT case:** when inside/outside are unset, still block private source crossing the router to a non-adjacent owner (so the without-PAT test is red until PAT is applied). After PAT, `nat_role` + `nat_overload` clear the block.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/netsim/test_nat_path.py tests/netsim/test_acl_path.py -v`

Expected: all PASS. ACL tests must not regress.

- [ ] **Step 7: Coach hint**

In `explain_unreachable`, after the ACL hint:

```python
if self._nat_would_block_explain(from_device, dst):
    return (
        "Traffic from a private inside host toward an outside address "
        "needs PAT on the border router."
    )
```

Add a test that the hint appears for the no-PAT topology.

- [ ] **Step 8: Commit**

```bash
git add src/openboson/netsim/ios/device.py src/openboson/netsim/ios/shell.py src/openboson/netsim/ios/world.py tests/netsim/test_nat_path.py
git commit -m "Require PAT overload for inside-host pings to outside peers."
```

---

### Task 4: Docs + gold lab still loads

**Files:**
- Modify: `docs/openios-command-matrix.md`
- Test: `tests/netsim/test_lab_loader.py` (existing)

- [ ] **Step 1: Update the NAT row**

In `docs/openios-command-matrix.md`, change the NAT line to:

```
| NAT | `ip nat inside/outside`, `ip nat inside source list … overload` | PAT required for inside PC → outside peer ping (ACL list not evaluated) |
```

Under Grading notes add:

```
- Inside-to-outside ICMP requires PAT overload on the border router. The NAT ACL is not evaluated in this model.
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/netsim/test_nat_path.py tests/netsim/test_acl_path.py tests/netsim/test_lab_loader.py tests/netsim/test_grader.py -q`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/openios-command-matrix.md
git commit -m "Document PAT packet effect in the OpenIOS command matrix."
```

---

### Task 5: Track exit

- [ ] **Step 1: Full netsim + lab GUI**

Run: `python -m pytest tests/netsim tests/gui/test_lab_flow.py -q`

Expected: all PASS

- [ ] **Step 2: Do not rewrite `ccna_nat_pat_edge.yaml` in this branch.** That is plan `2026-09-03-gold-lab-tickets.md`. This branch only makes ping honest.

- [ ] **Step 3: Stop.** Merge or keep `feat/honest-nat` ready. Next plan: `2026-09-03-honest-dhcp.md`.
