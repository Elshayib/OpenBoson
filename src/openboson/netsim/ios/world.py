"""LabWorld — multi-device topology runtime + L3 reachability (ping)."""

from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import Any

from openboson.netsim.ios.device import DeviceRole, DeviceRuntime, InterfaceState
from openboson.netsim.ios.host import HostShell
from openboson.netsim.ios.shell import OpenIOSShell
from openboson.netsim.lab_schema import LabBank


@dataclass
class LabWorld:
    """All devices in a lab + shells + simple topology-aware ping."""

    lab_id: str
    devices: dict[str, DeviceRuntime] = field(default_factory=dict)
    shells: dict[str, Any] = field(default_factory=dict)
    links: list[tuple[str, str, str, str]] = field(default_factory=list)
    # (dev_a, if_a, dev_b, if_b)

    @classmethod
    def from_lab(cls, lab: LabBank) -> "LabWorld":
        world = cls(lab_id=lab.lab_id)
        topo = lab.topology
        for d in topo.devices:
            role = DeviceRole(d.type.value if hasattr(d.type, "value") else d.type)
            runtime = DeviceRuntime(name=d.name, role=role, hostname=d.name)
            for iface in d.interfaces:
                ip = mask = None
                if iface.ip and "/" in iface.ip:
                    addr, _, pref = iface.ip.partition("/")
                    ip = addr
                    try:
                        mask = str(IPv4Network(f"0.0.0.0/{pref}").netmask)
                    except ValueError:
                        mask = None
                elif iface.ip:
                    ip = iface.ip
                # Routers: interfaces down until no shut.
                # Switches/PCs: ports start up (more realistic desk).
                admin = role != DeviceRole.ROUTER
                st = InterfaceState(
                    name=iface.name,
                    ip=ip,
                    mask=mask,
                    admin_up=admin,
                    protocol_up=False,
                    connected_to=iface.connected_to,
                )
                runtime.interfaces[iface.name] = st
            world.devices[d.name] = runtime
            if role == DeviceRole.PC:
                world.shells[d.name] = HostShell(runtime, world=world)
            else:
                world.shells[d.name] = OpenIOSShell(runtime, world=world)

        for link in topo.links:
            a_dev, a_if = _split_endpoint(link.a)
            b_dev, b_if = _split_endpoint(link.b)
            world.links.append((a_dev, a_if, b_dev, b_if))
            if a_dev in world.devices and a_if in world.devices[a_dev].interfaces:
                world.devices[a_dev].interfaces[a_if].connected_to = f"{b_dev}/{b_if}"
            if b_dev in world.devices and b_if in world.devices[b_dev].interfaces:
                world.devices[b_dev].interfaces[b_if].connected_to = f"{a_dev}/{a_if}"

        world._refresh_link_state()
        return world

    def shell(self, device_name: str) -> Any:
        if device_name not in self.shells:
            raise KeyError(device_name)
        return self.shells[device_name]

    def device_names(self) -> list[str]:
        return list(self.devices.keys())

    def running_configs(self) -> dict[str, str]:
        return {n: d.running_config() for n, d in self.devices.items()}

    def combined_running_config(self) -> str:
        parts = []
        for n, cfg in self.running_configs().items():
            parts.append(f"! --- {n} ---\n{cfg}")
        return "\n".join(parts)

    def link_states(self) -> list[dict[str, Any]]:
        """Return link LED state for the topology canvas."""
        self._refresh_link_state()
        out = []
        for a_dev, a_if, b_dev, b_if in self.links:
            ia = self.devices[a_dev].interfaces.get(a_if)
            ib = self.devices[b_dev].interfaces.get(b_if)
            up = bool(ia and ib and ia.admin_up and ib.admin_up and ia.protocol_up)
            out.append(
                {
                    "a": f"{a_dev}/{a_if}",
                    "b": f"{b_dev}/{b_if}",
                    "up": up,
                    "a_dev": a_dev,
                    "b_dev": b_dev,
                }
            )
        return out

    def device_tooltip(self, name: str) -> str:
        dev = self.devices.get(name)
        if not dev:
            return name
        lines = [f"{name}  ({dev.role.value})", f"hostname: {dev.hostname}"]
        for iname, iface in sorted(dev.interfaces.items()):
            st = "up" if iface.admin_up else "down"
            ip = f"{iface.ip}/{iface.mask}" if iface.ip and iface.mask else "unassigned"
            lines.append(f"  {iname}: {ip} [{st}]")
        return "\n".join(lines)

    def notify_link_change(self, device: str, ifname: str) -> str:
        """Called after admin state changes; returns syslog-style lines."""
        self._refresh_link_state()
        iface = self.devices[device].interfaces.get(ifname)
        if not iface:
            return ""
        st, proto = iface.status_pair()
        # IOS-like line protocol message
        if iface.admin_up and iface.protocol_up:
            return (
                f"%LINK-3-UPDOWN: Interface {ifname}, changed state to up\n"
                f"%LINEPROTO-5-UPDOWN: Line protocol on Interface {ifname}, changed state to up"
            )
        if iface.admin_up and not iface.protocol_up:
            return (
                f"%LINK-3-UPDOWN: Interface {ifname}, changed state to up\n"
                f"%LINEPROTO-5-UPDOWN: Line protocol on Interface {ifname}, changed state to down"
            )
        return (
            f"%LINK-5-CHANGED: Interface {ifname}, changed state to administratively down\n"
            f"%LINEPROTO-5-UPDOWN: Line protocol on Interface {ifname}, changed state to down"
        )

    def _refresh_link_state(self) -> None:
        for a_dev, a_if, b_dev, b_if in self.links:
            a = self.devices.get(a_dev)
            b = self.devices.get(b_dev)
            if not a or not b:
                continue
            ia = a.interfaces.get(a_if)
            ib = b.interfaces.get(b_if)
            if not ia or not ib:
                continue
            up = bool(ia.admin_up and ib.admin_up)
            ia.protocol_up = up
            ib.protocol_up = up

    def ping(self, from_device: str, target_ip: str) -> str:
        self._refresh_link_state()
        try:
            dst = IPv4Address(target_ip)
        except ValueError:
            return "% Unrecognized host or address."

        src = self.devices.get(from_device)
        if src is None:
            return "% Source device not found."

        path_ok = self._can_reach(from_device, dst)
        header = (
            f"Type escape sequence to abort.\n"
            f"Sending 5, 100-byte ICMP Echos to {target_ip}, timeout is 2 seconds:\n"
        )
        if path_ok:
            return (
                header
                + "!!!!!\n"
                + "Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/4 ms"
            )
        return header + ".....\n" + "Success rate is 0 percent (0/5)"

    def traceroute(self, from_device: str, target_ip: str) -> str:
        self._refresh_link_state()
        try:
            dst = IPv4Address(target_ip)
        except ValueError:
            return f"Tracing the route to {target_ip}\n  1  * * *"
        ok = self._can_reach(from_device, dst)
        lines = [
            f"Type escape sequence to abort.",
            f"Tracing the route to {target_ip}",
            "",
        ]
        if ok:
            hops = self._hop_ips(from_device, dst)
            for i, hop in enumerate(hops, 1):
                lines.append(f"  {i} {hop} 1 msec 1 msec 1 msec")
            if not hops:
                lines.append(f"  1 {target_ip} 1 msec 1 msec 1 msec")
        else:
            lines.append("  1  * * *")
            lines.append("  2  * * *")
        return "\n".join(lines)

    def _owner_of_ip(self, ip: IPv4Address) -> str | None:
        for name, dev in self.devices.items():
            for iface in dev.interfaces.values():
                if iface.ip and iface.admin_up:
                    try:
                        if IPv4Address(iface.ip) == ip:
                            return name
                    except ValueError:
                        continue
        return None

    def _can_reach(self, from_device: str, dst: IPv4Address) -> bool:
        src = self.devices.get(from_device)
        if src is None:
            return False
        for iface in src.interfaces.values():
            if iface.admin_up and iface.ip:
                try:
                    if IPv4Address(iface.ip) == dst:
                        return True
                except ValueError:
                    pass
        for net, _ in self._connected_subnets(from_device):
            if dst in net:
                owner = self._owner_of_ip(dst)
                if owner is None or owner == from_device:
                    return True
                return self._l2_adjacent_or_same(from_device, owner) or self._routed(
                    from_device, dst
                )
        return self._routed(from_device, dst)

    def _connected_subnets(self, device: str) -> list[tuple[IPv4Network, str]]:
        dev = self.devices[device]
        out: list[tuple[IPv4Network, str]] = []
        for iname, iface in dev.interfaces.items():
            if iface.admin_up and iface.ip and iface.mask:
                try:
                    net = IPv4Interface(f"{iface.ip}/{iface.mask}").network
                    out.append((net, iname))
                except ValueError:
                    continue
        return out

    def _l2_adjacent_or_same(self, a: str, b: str) -> bool:
        if a == b:
            return True
        direct = self._direct_link_up(a, b)
        if direct and self._vlan_compatible(a, b, None):
            return True
        for mid in self.devices:
            if mid in {a, b}:
                continue
            if self.devices[mid].role != DeviceRole.SWITCH:
                continue
            if not (self._direct_link_up(a, mid) and self._direct_link_up(mid, b)):
                continue
            if self._hosts_share_access_vlan(mid, a, b):
                return True
        return False

    def _iface_toward(self, switch: str, peer: str) -> InterfaceState | None:
        for a_dev, a_if, b_dev, b_if in self.links:
            if a_dev == switch and b_dev == peer:
                return self.devices[switch].interfaces.get(a_if)
            if b_dev == switch and a_dev == peer:
                return self.devices[switch].interfaces.get(b_if)
        return None

    def _hosts_share_access_vlan(self, switch: str, a: str, b: str) -> bool:
        ia = self._iface_toward(switch, a)
        ib = self._iface_toward(switch, b)
        if ia is None or ib is None:
            return False
        # Trunk toward router/other switch can bridge; access ports must match VLAN.
        if ia.switchport_mode == "trunk" or ib.switchport_mode == "trunk":
            return True
        va = ia.access_vlan if ia.switchport_mode == "access" else 1
        vb = ib.access_vlan if ib.switchport_mode == "access" else 1
        if va is None:
            va = 1
        if vb is None:
            vb = 1
        return va == vb

    def _vlan_compatible(self, a: str, b: str, _switch: str | None) -> bool:
        return True

    def _direct_link_up(self, a: str, b: str) -> bool:
        for a_dev, a_if, b_dev, b_if in self.links:
            if {a_dev, b_dev} != {a, b}:
                continue
            ia = self.devices[a_dev].interfaces[a_if]
            ib = self.devices[b_dev].interfaces[b_if]
            return bool(ia.admin_up and ib.admin_up and ia.protocol_up and ib.protocol_up)
        return False

    def _routed(self, from_device: str, dst: IPv4Address) -> bool:
        dev = self.devices[from_device]
        for r in dev.static_routes:
            try:
                net = IPv4Network(f"{r.network}/{r.mask}", strict=False)
                nh = IPv4Address(r.next_hop)
            except ValueError:
                continue
            if dst not in net:
                continue
            for cnet, _ in self._connected_subnets(from_device):
                if nh in cnet:
                    owner = self._owner_of_ip(nh)
                    if owner and self._l2_adjacent_or_same(from_device, owner):
                        return self._can_reach_simple(owner, dst, depth=1)
                    return True
        return False

    def _can_reach_simple(self, from_device: str, dst: IPv4Address, depth: int) -> bool:
        if depth > 4:
            return False
        for net, _ in self._connected_subnets(from_device):
            if dst in net:
                return True
        return False

    def _hop_ips(self, from_device: str, dst: IPv4Address) -> list[str]:
        owner = self._owner_of_ip(dst)
        hops: list[str] = []
        if owner and owner != from_device:
            for a_dev, a_if, b_dev, b_if in self.links:
                if from_device == a_dev and owner == b_dev:
                    ip = self.devices[b_dev].interfaces[b_if].ip
                    if ip:
                        hops.append(ip)
                elif from_device == b_dev and owner == a_dev:
                    ip = self.devices[a_dev].interfaces[a_if].ip
                    if ip:
                        hops.append(ip)
        hops.append(str(dst))
        return hops


def _split_endpoint(ep: str) -> tuple[str, str]:
    if "/" not in ep:
        return ep, ""
    dev, _, rest = ep.partition("/")
    return dev, rest
