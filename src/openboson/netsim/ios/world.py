"""LabWorld — multi-device topology runtime + L3 reachability (ping)."""

from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import Any

from openboson.netsim.ios.device import DeviceRole, DeviceRuntime, InterfaceState, StaticRoute
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
    def from_lab(cls, lab: LabBank) -> LabWorld:
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
        self._rebuild_ospf_routes()
        try:
            dst = IPv4Address(target_ip)
        except ValueError:
            return "% Unrecognized host or address."

        src = self.devices.get(from_device)
        if src is None:
            return "% Source device not found."

        path_ok = self._can_reach(from_device, dst)
        if path_ok:
            self._learn_arp_on_success(from_device, dst)
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

    def explain_unreachable(self, from_device: str, target_ip: str) -> str:
        """Short coach hint for a failed ping (no solution commands)."""
        try:
            dst = IPv4Address(target_ip)
        except ValueError:
            return "Destination address is not a valid IPv4 host."
        src = self.devices.get(from_device)
        if src is None:
            return "Source device is missing from the lab world."
        if not any(i.admin_up and i.ip for i in src.interfaces.values()):
            return f"{from_device} has no operational interface address yet."
        owner = self._owner_of_ip(dst)
        if owner is None:
            return "No device in this lab owns that destination address."
        if self._acl_blocks_icmp(from_device, dst):
            return "An access list on the path is denying this ICMP traffic."
        if (
            owner != from_device
            and not self._l2_adjacent_or_same(from_device, owner)
            and not self._routed(from_device, dst)
        ):
            return (
                "No L2 adjacency or route from the source toward that destination — "
                "check VLANs, links, addressing, and routing."
            )
        return "Path check failed — verify addressing, VLANs, links, and filters."

    def _acl_blocks_icmp(self, from_device: str, dst: IPv4Address) -> bool:
        """Return True if a simplified ACL on the path denies ICMP to dst."""
        src_ip = self._primary_ip(from_device)
        if src_ip is None:
            return False
        for name, dev in self.devices.items():
            if dev.role not in (DeviceRole.ROUTER, DeviceRole.FIREWALL):
                continue
            applied = self._applied_acl_ids(dev)
            if not applied:
                continue
            owner = self._owner_of_ip(dst)
            if name not in {from_device, owner} and not (
                self._l2_adjacent_or_same(from_device, name)
                or (owner is not None and self._l2_adjacent_or_same(name, owner))
            ):
                continue
            for acl_id in applied:
                decision = self._acl_decision(dev, acl_id, src_ip, dst)
                if decision is False:
                    return True
        return False

    def _primary_ip(self, device: str) -> IPv4Address | None:
        dev = self.devices.get(device)
        if not dev:
            return None
        for iface in dev.interfaces.values():
            if iface.admin_up and iface.ip:
                try:
                    return IPv4Address(iface.ip)
                except ValueError:
                    continue
        return None

    def _applied_acl_ids(self, dev: DeviceRuntime) -> list[str]:
        ids: list[str] = []
        for iface in dev.interfaces.values():
            for line in iface.extra_lines:
                parts = line.split()
                if (
                    len(parts) >= 4
                    and parts[0].lower() == "ip"
                    and parts[1].lower() == "access-group"
                ):
                    ids.append(parts[2])
        return ids

    def _acl_decision(
        self, dev: DeviceRuntime, acl_id: str, src: IPv4Address, dst: IPv4Address
    ) -> bool | None:
        """First-match ACL: True=permit, False=deny, None=no matching ACL lines."""
        rules = self._acl_rules(dev, acl_id)
        if not rules:
            return None
        for action, kind, src_tok, dst_tok in rules:
            if not self._acl_token_match(kind, src_tok, dst_tok, src, dst):
                continue
            return action == "permit"
        return False

    def _acl_rules(self, dev: DeviceRuntime, acl_id: str) -> list[tuple[str, str, str, str]]:
        out: list[tuple[str, str, str, str]] = []
        for raw in dev.extra_global:
            line = raw.strip()
            low = line.lower()
            if low.startswith("ip access-list") or not low.startswith("access-list "):
                continue
            parts = line.split()
            if len(parts) < 3 or parts[1] != acl_id:
                continue
            action = parts[2].lower()
            if action not in {"permit", "deny"}:
                continue
            rest = [p.lower() for p in parts[3:]]
            if not rest:
                continue
            if rest[0] == "any" and len(rest) == 1:
                out.append((action, "any", "any", "any"))
                continue
            if rest[0] == "host" and len(rest) >= 2:
                out.append((action, "host", rest[1], rest[1]))
                continue
            proto = rest[0]
            if proto in {"ip", "icmp", "tcp", "udp"}:
                src_tok, dst_tok = "any", "any"
                i = 1
                if i < len(rest):
                    if rest[i] == "any":
                        src_tok = "any"
                        i += 1
                    elif rest[i] == "host" and i + 1 < len(rest):
                        src_tok = rest[i + 1]
                        i += 2
                if i < len(rest):
                    if rest[i] == "any":
                        dst_tok = "any"
                    elif rest[i] == "host" and i + 1 < len(rest):
                        dst_tok = rest[i + 1]
                out.append((action, proto, src_tok, dst_tok))
                continue
            out.append((action, "std", rest[0], rest[0]))
        return out

    def _acl_token_match(
        self,
        kind: str,
        src_tok: str,
        dst_tok: str,
        src: IPv4Address,
        dst: IPv4Address,
    ) -> bool:
        if kind == "any":
            return True

        def _one(tok: str, ip: IPv4Address) -> bool:
            if tok == "any":
                return True
            try:
                return IPv4Address(tok) == ip
            except ValueError:
                return False

        if kind == "host":
            return _one(dst_tok, dst)
        if kind in {"ip", "icmp"}:
            return _one(src_tok, src) and _one(dst_tok, dst)
        if kind == "std":
            return _one(dst_tok, dst) or _one(src_tok, dst)
        return False

    def show_arp(self, device: str) -> str:
        """Render a compact ``show ip arp`` table for ``device``."""
        dev = self.devices.get(device)
        if dev is None:
            return "% Device not found."
        lines = [
            "Protocol  Address          Age (min)  Hardware Addr   Type   Interface",
        ]
        # Connected interface IPs appear as local/incomplete until learned.
        for iname, iface in sorted(dev.interfaces.items()):
            if iface.ip and iface.admin_up:
                mac = dev.arp_table.get(iface.ip) or dev.mac_for_iface(iname)
                lines.append(f"Internet  {iface.ip:<15}  -          {mac}  ARPA   {iname}")
        for ip, mac in sorted(dev.arp_table.items()):
            if any(iface.ip == ip for iface in dev.interfaces.values()):
                continue
            lines.append(f"Internet  {ip:<15}  0          {mac}  ARPA")
        if len(lines) == 1:
            lines.append("")
        return "\n".join(lines)

    def _learn_arp_on_success(self, from_device: str, dst: IPv4Address) -> None:
        src = self.devices[from_device]
        owner = self._owner_of_ip(dst)
        if owner is None:
            return
        peer = self.devices[owner]
        # Pick a connected iface MAC on the owner when possible.
        mac = "aabb.cc00.0001"
        for iname, iface in peer.interfaces.items():
            if iface.ip and iface.admin_up:
                try:
                    if IPv4Address(iface.ip) == dst:
                        mac = peer.mac_for_iface(iname)
                        break
                except ValueError:
                    continue
            else:
                mac = peer.mac_for_iface(iname)
        src.learn_arp(str(dst), mac)

    def traceroute(self, from_device: str, target_ip: str) -> str:
        self._refresh_link_state()
        self._rebuild_ospf_routes()
        try:
            dst = IPv4Address(target_ip)
        except ValueError:
            return f"Tracing the route to {target_ip}\n  1  * * *"
        ok = self._can_reach(from_device, dst)
        lines = [
            "Type escape sequence to abort.",
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
        if self._acl_blocks_icmp(from_device, dst):
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
        return self._follow_routes(from_device, dst, include_ospf=True)

    def _follow_routes(self, from_device: str, dst: IPv4Address, *, include_ospf: bool) -> bool:
        dev = self.devices[from_device]
        routes: list[StaticRoute] = list(dev.static_routes)
        if include_ospf:
            routes.extend(dev.ospf_routes)
        for r in routes:
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

    def _rebuild_ospf_routes(self) -> None:
        """Install simplified OSPF routes between adjacent OSPF routers."""
        for dev in self.devices.values():
            dev.ospf_routes.clear()

        speakers: dict[str, list[IPv4Network]] = {}
        for name, dev in self.devices.items():
            nets = self._ospf_advertised_networks(dev)
            if nets:
                speakers[name] = nets
        if len(speakers) < 2:
            return

        for a_name in speakers:
            a_dev = self.devices[a_name]
            for b_name, b_nets in speakers.items():
                if a_name == b_name:
                    continue
                if not self._l2_adjacent_or_same(a_name, b_name):
                    continue
                nh = self._peer_ip_on_link(a_name, b_name)
                if not nh:
                    continue
                connected = {n for n, _ in self._connected_subnets(a_name)}
                for net in b_nets:
                    if any(net == c or net.subnet_of(c) or c.subnet_of(net) for c in connected):
                        continue
                    if any(
                        IPv4Network(f"{r.network}/{r.mask}", strict=False) == net
                        for r in a_dev.static_routes + a_dev.ospf_routes
                    ):
                        continue
                    a_dev.ospf_routes.append(
                        StaticRoute(
                            network=str(net.network_address),
                            mask=str(net.netmask),
                            next_hop=nh,
                        )
                    )

    def _ospf_advertised_networks(self, dev) -> list[IPv4Network]:
        """Return connected nets that match ``network … area`` under ``router ospf``."""
        if not any(line.lower().startswith("router ospf") for line in (dev.extra_global or [])):
            return []
        statements: list[tuple[IPv4Address, IPv4Address]] = []
        for line in dev.extra_global:
            parts = line.split()
            if len(parts) < 5 or parts[0].lower() != "network":
                continue
            if parts[3].lower() != "area":
                continue
            try:
                network = IPv4Address(parts[1])
                wildcard = IPv4Address(parts[2])
            except ValueError:
                continue
            statements.append((network, wildcard))
        if not statements:
            return []
        out: list[IPv4Network] = []
        for iface in dev.interfaces.values():
            if not (iface.admin_up and iface.ip and iface.mask and iface.network):
                continue
            try:
                ip = IPv4Address(iface.ip)
            except ValueError:
                continue
            for network, wildcard in statements:
                # Cisco: (ip & ~wc) == (network & ~wc)
                mask_int = (~int(wildcard)) & 0xFFFFFFFF
                if (int(ip) & mask_int) == (int(network) & mask_int):
                    out.append(iface.network)
                    break
        return out

    def _peer_ip_on_link(self, from_device: str, peer: str) -> str | None:
        for a_dev, a_if, b_dev, b_if in self.links:
            if a_dev == from_device and b_dev == peer:
                return self.devices[peer].interfaces[b_if].ip
            if b_dev == from_device and a_dev == peer:
                return self.devices[peer].interfaces[a_if].ip
        return None

    def _can_reach_simple(self, from_device: str, dst: IPv4Address, depth: int) -> bool:
        if depth > 4:
            return False
        for net, _ in self._connected_subnets(from_device):
            if dst not in net:
                continue
            owner = self._owner_of_ip(dst)
            if owner is None or owner == from_device:
                return True
            return self._l2_adjacent_or_same(from_device, owner)
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
