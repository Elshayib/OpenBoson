"""Host shell for PC endpoints — ipconfig / ping / tracert style."""

from __future__ import annotations

import re
from dataclasses import dataclass

from openboson.netsim.ios.device import DeviceRuntime, parse_ip_mask
from openboson.netsim.ios.shell import ShellResult


@dataclass
class HostShell:
    """Simple host CLI bound to a PC DeviceRuntime.

    Same feed/prompt/banner/complete surface as OpenIOSShell so the terminal
    widget can bind either without branching.
    """

    device: DeviceRuntime
    world: object | None = None
    history: list[str] | None = None

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = []
        # Hosts are "up" by default on their primary interface.
        for iface in self.device.interfaces.values():
            iface.admin_up = True

    def prompt(self) -> str:
        return f"{self.device.hostname}>"

    def banner(self) -> str:
        return (
            f"\nOpenBoson Host Shell — '{self.device.name}'\n"
            f"Commands: ipconfig, ping, tracert, ip address, help, ?\n"
            f"\n"
            f"{self.prompt()}"
        )

    def feed(self, line: str) -> ShellResult:
        raw = line.rstrip("\r\n")
        if raw.strip():
            self.history.append(raw)  # type: ignore[union-attr]
        stripped = raw.strip()
        if not stripped:
            return ShellResult(output="")
        if stripped in {"?", "help"}:
            return ShellResult(output=self._help())
        if stripped.endswith("?"):
            return ShellResult(output=self._help())

        parts = stripped.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in {"ipconfig", "ifconfig"}:
            return ShellResult(output=self._ipconfig(args))
        if cmd == "ping":
            return ShellResult(output=self._ping(args))
        if cmd in {"tracert", "traceroute"}:
            return ShellResult(output=self._tracert(args))
        if cmd == "ip":
            return ShellResult(output=self._ip(args))
        if cmd in {"cls", "clear"}:
            return ShellResult(output="\x1b[2J")  # terminal may ignore
        if cmd in {"exit", "quit", "logout"}:
            return ShellResult(output="")
        return ShellResult(
            output=f"'{parts[0]}' is not recognized as an internal or external command."
        )

    def complete(self, partial: str) -> list[str]:
        cmds = ["ipconfig", "ping", "tracert", "ip", "help", "cls"]
        token = partial.strip().split()[-1] if partial.strip() else ""
        if not partial.strip() or partial.endswith(" "):
            return cmds
        return [c for c in cmds if c.startswith(token.lower())]

    def _help(self) -> str:
        return (
            "  ipconfig                 Display IP configuration\n"
            "  ipconfig /all            Display full configuration\n"
            "  ip address <ip> <mask>   Set static address on primary NIC\n"
            "  ping <host>              ICMP echo\n"
            "  tracert <host>           Trace route\n"
            f"\n{self.prompt()}"
        )

    def _primary(self):
        if not self.device.interfaces:
            return None
        # Prefer first interface
        return next(iter(self.device.interfaces.values()))

    def _ipconfig(self, args: list[str]) -> str:
        iface = self._primary()
        if iface is None:
            return "No network adapters."
        wide = any(a.lower() in {"/all", "-all", "all"} for a in args)
        ip = iface.ip or "0.0.0.0"
        mask = iface.mask or "0.0.0.0"
        gw = self._guess_gateway()
        lines = [
            "Windows IP Configuration" if wide else "IP Configuration",
            "",
            f"Ethernet adapter {iface.name}:",
            "",
            "   Connection-specific DNS Suffix  . :",
            f"   IPv4 Address. . . . . . . . . . . : {ip}",
            f"   Subnet Mask . . . . . . . . . . . : {mask}",
            f"   Default Gateway . . . . . . . . . : {gw or ''}",
        ]
        if wide:
            lines.insert(5, "   Description . . . . . . . . . . . : OpenBoson Virtual NIC")
            lines.insert(6, "   Physical Address. . . . . . . . . : AA-BB-CC-00-01-10")
            lines.append("   DHCP Enabled. . . . . . . . . . . : No")
        return "\n".join(lines)

    def _guess_gateway(self) -> str | None:
        iface = self._primary()
        if not iface or not iface.ip or not iface.mask:
            return None
        # Convention: .1 on same subnet
        try:
            parts = iface.ip.split(".")
            parts[-1] = "1"
            return ".".join(parts)
        except Exception:
            return None

    def _ip(self, args: list[str]) -> str:
        # ip address 10.10.10.10 255.255.255.0
        # ip addr ...
        if not args:
            return "Usage: ip address <ip> <mask>"
        if args[0].lower() in {"address", "addr", "a"}:
            args = args[1:]
        if len(args) < 2:
            return "Usage: ip address <ip> <mask>"
        parsed = parse_ip_mask(args[0], args[1])
        if not parsed:
            return "Invalid IP address or subnet mask."
        iface = self._primary()
        if iface is None:
            return "No network adapters."
        iface.ip, iface.mask = parsed
        iface.admin_up = True
        iface.protocol_up = True
        if self.world is not None and hasattr(self.world, "_refresh_link_state"):
            self.world._refresh_link_state()  # type: ignore[attr-defined]
        return ""

    def _ping(self, args: list[str]) -> str:
        if not args:
            return "Usage: ping <host>"
        target = args[0]
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
            return (
                f"Ping request could not find host {target}. Please check the name and try again."
            )
        if self.world is not None and hasattr(self.world, "ping"):
            # Reuse world ping but format slightly more host-like if success/fail
            raw = self.world.ping(self.device.name, target)  # type: ignore[attr-defined]
            if "100 percent" in raw:
                return (
                    f"Pinging {target} with 32 bytes of data:\n"
                    f"Reply from {target}: bytes=32 time=1ms TTL=64\n"
                    f"Reply from {target}: bytes=32 time=1ms TTL=64\n"
                    f"Reply from {target}: bytes=32 time=1ms TTL=64\n"
                    f"Reply from {target}: bytes=32 time=2ms TTL=64\n"
                    f"\n"
                    f"Ping statistics for {target}:\n"
                    f"    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),\n"
                    f"Approximate round trip times in milli-seconds:\n"
                    f"    Minimum = 1ms, Maximum = 2ms, Average = 1ms"
                )
            return (
                f"Pinging {target} with 32 bytes of data:\n"
                f"Request timed out.\n"
                f"Request timed out.\n"
                f"Request timed out.\n"
                f"Request timed out.\n"
                f"\n"
                f"Ping statistics for {target}:\n"
                f"    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),"
            )
        return f"Pinging {target} with 32 bytes of data:\nRequest timed out."

    def _tracert(self, args: list[str]) -> str:
        if not args:
            return "Usage: tracert <host>"
        target = args[0]
        if self.world is not None and hasattr(self.world, "traceroute"):
            raw = self.world.traceroute(self.device.name, target)  # type: ignore[attr-defined]
            # Convert lightly
            lines = [f"Tracing route to {target} over a maximum of 30 hops:", ""]
            for line in raw.splitlines():
                m = re.match(r"\s*(\d+)\s+(\S+)", line)
                if m:
                    lines.append(f"  {m.group(1)}    1 ms    1 ms    1 ms  {m.group(2)}")
            lines.append("")
            lines.append("Trace complete.")
            return "\n".join(lines)
        return f"Tracing route to {target}\n  1     *        *        *     Request timed out."
