"""Runtime device state for OpenIOS (interfaces, VLANs, routes, configs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import Any


class DeviceRole(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    AP = "ap"
    FIREWALL = "firewall"
    PC = "pc"


@dataclass
class InterfaceState:
    name: str
    description: str = ""
    ip: str | None = None  # "10.0.0.1"
    mask: str | None = None  # "255.255.255.0"
    admin_up: bool = False  # shutdown by default (IOS-like for unused)
    protocol_up: bool = False
    switchport_mode: str | None = None  # access | trunk | None
    access_vlan: int | None = None
    connected_to: str | None = None  # "SW1/GigabitEthernet0/1"

    @property
    def cidr(self) -> str | None:
        if self.ip and self.mask:
            try:
                return str(IPv4Interface(f"{self.ip}/{self.mask}"))
            except ValueError:
                return None
        return None

    @property
    def network(self) -> IPv4Network | None:
        c = self.cidr
        if not c:
            return None
        try:
            return IPv4Interface(c).network
        except ValueError:
            return None

    def status_pair(self) -> tuple[str, str]:
        """Return (Status, Protocol) strings like `show ip int brief`."""
        if not self.admin_up:
            return ("administratively down", "down")
        # Link is up if connected peer exists (world may refine later).
        if self.connected_to:
            return ("up", "up" if self.protocol_up or self.ip else "up")
        return ("up", "up" if self.protocol_up else "down")


@dataclass
class StaticRoute:
    network: str  # "10.0.0.0"
    mask: str
    next_hop: str


@dataclass
class DeviceRuntime:
    """Mutable runtime state for one simulated network device."""

    name: str
    role: DeviceRole = DeviceRole.ROUTER
    hostname: str = ""
    interfaces: dict[str, InterfaceState] = field(default_factory=dict)
    vlans: dict[int, str] = field(default_factory=dict)  # id -> name
    static_routes: list[StaticRoute] = field(default_factory=list)
    startup_config: str = ""
    banner_motd: str = ""
    # Extra freeform config lines under global that we don't model deeply.
    extra_global: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.hostname:
            self.hostname = self.name
        # Switches always have VLAN 1.
        if self.role == DeviceRole.SWITCH and 1 not in self.vlans:
            self.vlans[1] = "default"

    def get_iface(self, name: str) -> InterfaceState | None:
        # Case-insensitive + common abbreviations (g0/0, gi0/0, f0/0).
        key = _canon_if_name(name)
        for iname, iface in self.interfaces.items():
            if _canon_if_name(iname) == key:
                return iface
        # Also try partial match against known interfaces.
        for iname, iface in self.interfaces.items():
            if _if_matches(iname, name):
                return iface
        return None

    def resolve_if_name(self, name: str) -> str | None:
        iface = self.get_iface(name)
        return iface.name if iface else None

    def running_config(self) -> str:
        """Render an IOS-like running-config text dump."""
        lines: list[str] = ["!", f"hostname {self.hostname}", "!"]
        if self.banner_motd:
            lines += [f"banner motd ^{self.banner_motd}^", "!"]
        for vid in sorted(self.vlans):
            if vid == 1 and self.vlans[vid] == "default":
                continue
            lines.append(f"vlan {vid}")
            if self.vlans[vid]:
                lines.append(f" name {self.vlans[vid]}")
            lines.append("!")
        for name in sorted(self.interfaces):
            iface = self.interfaces[name]
            lines.append(f"interface {name}")
            if iface.description:
                lines.append(f" description {iface.description}")
            if iface.ip and iface.mask:
                lines.append(f" ip address {iface.ip} {iface.mask}")
            if iface.switchport_mode == "trunk":
                lines.append(" switchport trunk encapsulation dot1q")
                lines.append(" switchport mode trunk")
            elif iface.switchport_mode == "access":
                lines.append(" switchport mode access")
                if iface.access_vlan is not None:
                    lines.append(f" switchport access vlan {iface.access_vlan}")
            if iface.admin_up:
                lines.append(" no shutdown")
            else:
                lines.append(" shutdown")
            lines.append("!")
        for r in self.static_routes:
            lines.append(f"ip route {r.network} {r.mask} {r.next_hop}")
        for extra in self.extra_global:
            lines.append(extra)
        lines.append("end")
        return "\n".join(lines)

    def show_ip_int_brief(self) -> str:
        header = (
            f"{'Interface':<28}{'IP-Address':<16}{'OK?':<4}"
            f"{'Method':<8}{'Status':<22}{'Protocol'}"
        )
        rows = [header]
        for name in sorted(self.interfaces):
            iface = self.interfaces[name]
            st, proto = iface.status_pair()
            ip = iface.ip or "unassigned"
            rows.append(
                f"{name:<28}{ip:<16}{'YES':<4}{'manual':<8}{st:<22}{proto}"
            )
        return "\n".join(rows)

    def show_vlan_brief(self) -> str:
        if self.role not in (DeviceRole.SWITCH, DeviceRole.AP):
            return "% Incomplete command / not supported on this platform."
        lines = [
            f"{'VLAN':<6}{'Name':<20}{'Status':<10}Ports",
            f"{'----':<6}{'----':<20}{'------':<10}-----",
        ]
        # Map access ports to VLANs.
        ports_by_vlan: dict[int, list[str]] = {vid: [] for vid in self.vlans}
        for name, iface in self.interfaces.items():
            if iface.switchport_mode == "access" and iface.access_vlan:
                ports_by_vlan.setdefault(iface.access_vlan, []).append(name)
            elif iface.switchport_mode != "trunk":
                # Default VLAN 1
                ports_by_vlan.setdefault(1, []).append(name)
        for vid in sorted(self.vlans):
            name = self.vlans[vid]
            ports = ", ".join(ports_by_vlan.get(vid, []))
            lines.append(f"{vid:<6}{name:<20}{'active':<10}{ports}")
        return "\n".join(lines)

    def show_ip_route(self) -> str:
        lines = [
            f"Codes: C - connected, S - static",
            "",
            f"Gateway of last resort is not set",
            "",
        ]
        # Connected routes from up interfaces with IP.
        for name, iface in sorted(self.interfaces.items()):
            if iface.admin_up and iface.ip and iface.mask and iface.network:
                net = iface.network
                lines.append(
                    f"C    {net.network_address} /{net.prefixlen} is directly connected, {name}"
                )
        for r in self.static_routes:
            try:
                net = IPv4Network(f"{r.network}/{r.mask}", strict=False)
                lines.append(
                    f"S    {net.network_address} /{net.prefixlen} [1/0] via {r.next_hop}"
                )
            except ValueError:
                lines.append(f"S    {r.network} {r.mask} via {r.next_hop}")
        if len(lines) == 4:
            lines.append("     (no routes)")
        return "\n".join(lines)

    def show_version(self) -> str:
        plat = {
            DeviceRole.ROUTER: "OpenBoson OpenIOS Software (C1900-UNIVERSALK9), Version 15.7(3)M, SIMULATED",
            DeviceRole.SWITCH: "OpenBoson OpenIOS Software (C2960-LANBASEK9), Version 15.2(7)E, SIMULATED",
            DeviceRole.PC: "OpenBoson Host Stack, Version 1.0, SIMULATED",
            DeviceRole.AP: "OpenBoson OpenIOS-AP Software, Version 15.3, SIMULATED",
            DeviceRole.FIREWALL: "OpenBoson OpenIOS-FW Software, Version 9.x, SIMULATED",
        }.get(self.role, "OpenBoson OpenIOS Software, SIMULATED")
        return (
            f"{plat}\n"
            f"Technical Support: https://github.com/openboson (community)\n"
            f"Copyright (c) OpenBoson contributors. Simulated platform only.\n"
            f"\n"
            f"ROM: Bootstrap program is OpenIOS boot loader\n"
            f"\n"
            f"{self.hostname} uptime is 0 days, 0 hours, 5 minutes\n"
            f"System returned to ROM by power-on\n"
            f"System image file is \"flash:openios-sim.bin\"\n"
            f"\n"
            f"This product contains cryptographic features — simulated only.\n"
        )


def mask_to_prefix(mask: str) -> int | None:
    try:
        return IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except ValueError:
        return None


def prefix_to_mask(prefix: int) -> str:
    return str(IPv4Network(f"0.0.0.0/{prefix}").netmask)


def parse_ip_mask(ip: str, mask_or_prefix: str) -> tuple[str, str] | None:
    """Accept dotted mask or /prefix or bare prefix length."""
    m = mask_or_prefix.strip()
    if m.startswith("/"):
        m = m[1:]
    if m.isdigit():
        try:
            mask = prefix_to_mask(int(m))
            IPv4Address(ip)
            return ip, mask
        except ValueError:
            return None
    try:
        IPv4Address(ip)
        IPv4Network(f"0.0.0.0/{m}")
        return ip, m
    except ValueError:
        return None


def _canon_if_name(name: str) -> str:
    return name.strip().lower().replace(" ", "")


# Map short forms → full IOS names (partial).
_IF_PREFIXES = (
    ("gigabitethernet", "GigabitEthernet"),
    ("fastethernet", "FastEthernet"),
    ("ethernet", "Ethernet"),
    ("loopback", "Loopback"),
    ("vlan", "Vlan"),
    ("serial", "Serial"),
)


def expand_interface_name(token: str) -> str:
    """Expand g0/0 → GigabitEthernet0/0, fa0/1 → FastEthernet0/1, etc."""
    t = token.strip()
    low = t.lower()
    # Already full-ish
    for short, full in (
        ("gi", "GigabitEthernet"),
        ("g", "GigabitEthernet"),
        ("fa", "FastEthernet"),
        ("f", "FastEthernet"),
        ("e", "Ethernet"),
        ("lo", "Loopback"),
        ("se", "Serial"),
        ("s", "Serial"),
    ):
        if low.startswith(short) and len(low) > len(short) and low[len(short)].isdigit():
            return full + t[len(short) :]
        if low.startswith(short) and "/" in low:
            # g0/0
            rest = t[len(short) :]
            if rest and (rest[0].isdigit() or rest[0] == "/"):
                return full + rest
    # gigabitethernet0/0
    for pref, full in _IF_PREFIXES:
        if low.startswith(pref):
            return full + t[len(pref) :]
    return t


def _if_matches(full: str, user: str) -> bool:
    exp = expand_interface_name(user)
    return _canon_if_name(full) == _canon_if_name(exp) or _canon_if_name(full).startswith(
        _canon_if_name(exp)
    )
