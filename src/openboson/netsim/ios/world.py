"""LabWorld — multi-device topology runtime + L3 reachability (ping)."""

from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Interface, IPv4Network

from openboson.netsim.ios.device import DeviceRole, DeviceRuntime, InterfaceState
from openboson.netsim.ios.shell import OpenIOSShell
from openboson.netsim.lab_schema import LabBank, Topology


@dataclass
class LabWorld:
    """All devices in a lab + shells + simple topology-aware ping."""

    lab_id: str
    devices: dict[str, DeviceRuntime] = field(default_factory=dict)
    shells: dict[str, OpenIOSShell] = field(default_factory=dict)
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
                st = InterfaceState(
                    name=iface.name,
                    ip=ip,
                    mask=mask,
                    # Lab starting state: interfaces down until student no-shut
                    # unless it's a PC (hosts usually up).
                    admin_up=(role == DeviceRole.PC),
                    protocol_up=False,
                    connected_to=iface.connected_to,
                )
                # For switches, leave switchport unconfigured until the student
                # sets it (keeps running-config clean for grading).
                runtime.interfaces[iface.name] = st
            world.devices[d.name] = runtime
            world.shells[d.name] = OpenIOSShell(runtime, world=world)

        for link in topo.links:
            a_dev, a_if = _split_endpoint(link.a)
            b_dev, b_if = _split_endpoint(link.b)
            world.links.append((a_dev, a_if, b_dev, b_if))
            # Ensure connected_to is set both ways
            if a_dev in world.devices and a_if in world.devices[a_dev].interfaces:
                world.devices[a_dev].interfaces[a_if].connected_to = f"{b_dev}/{b_if}"
            if b_dev in world.devices and b_if in world.devices[b_dev].interfaces:
                world.devices[b_dev].interfaces[b_if].connected_to = f"{a_dev}/{a_if}"

        world._refresh_link_state()
        return world

    def shell(self, device_name: str) -> OpenIOSShell:
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

    def _refresh_link_state(self) -> None:
        """Protocol up when both sides admin_up (simplified Ethernet)."""
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
            return f"% Unrecognized host or address."

        src = self.devices.get(from_device)
        if src is None:
            return "% Source device not found."

        # Is destination one of our interface IPs?
        owner = self._owner_of_ip(dst)
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
        # Destination host unreachable vs timeout
        if owner and owner != from_device:
            return (
                header
                + ".....\n"
                + "Success rate is 0 percent (0/5)"
            )
        return (
            header
            + ".....\n"
            + "Success rate is 0 percent (0/5)"
        )

    def traceroute(self, from_device: str, target_ip: str) -> str:
        self._refresh_link_state()
        ok = self._can_reach(from_device, IPv4Address(target_ip))
        lines = [
            f"Type escape sequence to abort.",
            f"Tracing the route to {target_ip}",
            "",
        ]
        if ok:
            # Single-hop or two-hop fake path
            hops = self._hop_ips(from_device, IPv4Address(target_ip))
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
        """Simplified L3: own IPs, connected subnets, or static routes."""
        src = self.devices.get(from_device)
        if src is None:
            return False

        # Always reachable: any of our own admin-up interface addresses.
        for iface in src.interfaces.values():
            if iface.admin_up and iface.ip:
                try:
                    if IPv4Address(iface.ip) == dst:
                        return True
                except ValueError:
                    pass

        # Directly connected subnets (interface admin up; protocol preferred).
        for net, _ in self._connected_subnets(from_device):
            if dst in net:
                owner = self._owner_of_ip(dst)
                if owner is None:
                    return True
                if owner == from_device:
                    return True
                return self._l2_adjacent_or_same(from_device, owner) or self._routed(
                    from_device, dst
                )
        return self._routed(from_device, dst)

    def _connected_subnets(self, device: str) -> list[tuple[IPv4Network, str]]:
        dev = self.devices[device]
        out: list[tuple[IPv4Network, str]] = []
        for iname, iface in dev.interfaces.items():
            # Admin up + IP is enough for connected route (IOS installs C route
            # when interface is up/up; we loosen to admin_up for lab friendliness
            # when peer not yet configured).
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
        for a_dev, a_if, b_dev, b_if in self.links:
            pair = {(a_dev, b_dev), (b_dev, a_dev)}
            if (a, b) in {(a_dev, b_dev), (b_dev, a_dev)}:
                ia = self.devices[a_dev].interfaces[a_if]
                ib = self.devices[b_dev].interfaces[b_if]
                return bool(ia.admin_up and ib.admin_up and ia.protocol_up and ib.protocol_up)
        return False

    def _routed(self, from_device: str, dst: IPv4Address) -> bool:
        dev = self.devices[from_device]
        for r in dev.static_routes:
            try:
                net = IPv4Network(f"{r.network}/{r.mask}", strict=False)
            except ValueError:
                continue
            if dst not in net:
                continue
            # next-hop must be reachable on a connected subnet
            try:
                nh = IPv4Address(r.next_hop)
            except ValueError:
                continue
            for cnet, _ in self._connected_subnets(from_device):
                if nh in cnet:
                    # Assume if next hop is a neighbor device IP and link up, ok
                    owner = self._owner_of_ip(nh)
                    if owner and self._l2_adjacent_or_same(from_device, owner):
                        # One more hop: can owner reach dst?
                        if owner == from_device:
                            return True
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
            # first hop = remote interface IP on the link
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
    # "R1/GigabitEthernet0/0"
    if "/" not in ep:
        return ep, ""
    dev, _, rest = ep.partition("/")
    return dev, rest
