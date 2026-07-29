"""OpenIOS interactive shell — modes, prompts, command dispatch, errors."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from openboson.netsim.ios.device import (
    DeviceRuntime,
    DeviceRole,
    StaticRoute,
    expand_interface_name,
    parse_ip_mask,
)


class Mode(str, Enum):
    USER = "user"  # >
    ENABLE = "enable"  # #
    CONFIG = "config"  # (config)#
    CONFIG_IF = "config-if"  # (config-if)#
    CONFIG_VLAN = "config-vlan"  # (config-vlan)#
    CONFIG_LINE = "config-line"  # (config-line)#
    CONFIG_ROUTER = "config-router"  # (config-router)#


@dataclass
class ShellResult:
    """Output of processing one line (or boot banner)."""

    output: str = ""
    # If True, caller should not reprint the prompt (rare).
    silent: bool = False


# Command tables: mode -> list of (name, handler_name, min_args help)
# Handlers are methods on OpenIOSShell.


class OpenIOSShell:
    """Stateful IOS-like CLI bound to one DeviceRuntime.

    Optional ``world`` (LabWorld) enables ping/traceroute across topology.
    """

    def __init__(self, device: DeviceRuntime, world: object | None = None) -> None:
        self.device = device
        self.world = world
        self.mode = Mode.USER
        self._if_ctx: str | None = None  # current interface name
        self._vlan_ctx: int | None = None
        self._line_ctx: str | None = None
        self._router_ctx: str | None = None
        self.history: list[str] = []
        self._paging = False

    # -----/ Prompt /-----
    def prompt(self) -> str:
        h = self.device.hostname or self.device.name
        if self.mode == Mode.USER:
            return f"{h}>"
        if self.mode == Mode.ENABLE:
            return f"{h}#"
        if self.mode == Mode.CONFIG:
            return f"{h}(config)#"
        if self.mode == Mode.CONFIG_IF:
            return f"{h}(config-if)#"
        if self.mode == Mode.CONFIG_VLAN:
            return f"{h}(config-vlan)#"
        if self.mode == Mode.CONFIG_LINE:
            return f"{h}(config-line)#"
        if self.mode == Mode.CONFIG_ROUTER:
            return f"{h}(config-router)#"
        return f"{h}>"

    def banner(self) -> str:
        return (
            f"\nOpenBoson OpenIOS Simulator — {self.device.role.value.upper()} '{self.device.name}'\n"
            f"This is a simulated CLI for training. Not affiliated with Cisco Systems.\n"
            f"Type '?' for help. Type 'enable' to enter privileged EXEC.\n"
            f"\n"
            f"{self.prompt()}"
        )

    # -----/ Entry points /-----
    def feed(self, line: str) -> ShellResult:
        """Process one user input line (without the prompt)."""
        raw = line.rstrip("\r\n")
        if raw.strip():
            self.history.append(raw)

        # Help: trailing ?
        stripped = raw.strip()
        if stripped.endswith("?") or stripped == "?":
            return ShellResult(output=self._help(stripped.rstrip("?").strip()))

        if not stripped:
            return ShellResult(output="")

        return self._dispatch(stripped)

    def complete(self, partial: str) -> list[str]:
        """Tab-completion candidates for the current mode."""
        cmds = self._commands_for_mode()
        token = partial.strip().split()[-1] if partial.strip() else ""
        if not partial.strip() or partial.endswith(" "):
            return sorted(cmds.keys())
        return sorted(c for c in cmds if c.startswith(token.lower()) or _abbrev_match(c, token))

    # -----/ Dispatch /-----
    def _dispatch(self, line: str) -> ShellResult:
        parts = _tokenize(line)
        if not parts:
            return ShellResult(output="")

        # Global exit-ish regardless
        cmd = parts[0]
        args = parts[1:]

        table = self._commands_for_mode()
        match = _resolve_command(cmd, list(table.keys()))
        if match is None:
            return ShellResult(output=_invalid_input(line, 0))
        if match == "__ambiguous__":
            cands = [c for c in table if _abbrev_match(c, cmd)]
            return ShellResult(
                output=f"% Ambiguous command:  \"{cmd}\"\n  " + ", ".join(cands)
            )

        handler = table[match]
        try:
            out = handler(args, line)
        except _CmdError as e:
            return ShellResult(output=str(e))
        return ShellResult(output=out or "")

    def _commands_for_mode(self) -> dict[str, Callable[[list[str], str], str]]:
        m = self.mode
        base: dict[str, Callable] = {}
        if m == Mode.USER:
            base = {
                "enable": self._cmd_enable,
                "exit": self._cmd_exit_user,
                "logout": self._cmd_exit_user,
                "ping": self._cmd_ping,
                "show": self._cmd_show_user,
                "terminal": self._cmd_terminal,
                "help": self._cmd_help_cmd,
            }
        elif m == Mode.ENABLE:
            base = {
                "disable": self._cmd_disable,
                "exit": self._cmd_exit_user,
                "end": self._cmd_end,
                "configure": self._cmd_configure,
                "show": self._cmd_show,
                "ping": self._cmd_ping,
                "traceroute": self._cmd_traceroute,
                "write": self._cmd_write,
                "copy": self._cmd_copy,
                "clear": self._cmd_clear,
                "reload": self._cmd_reload,
                "help": self._cmd_help_cmd,
            }
        elif m == Mode.CONFIG:
            base = {
                "hostname": self._cmd_hostname,
                "interface": self._cmd_interface,
                "vlan": self._cmd_vlan,
                "ip": self._cmd_ip_global,
                "no": self._cmd_no_global,
                "banner": self._cmd_banner,
                "line": self._cmd_line,
                "router": self._cmd_router,
                "do": self._cmd_do,
                "exit": self._cmd_exit_config,
                "end": self._cmd_end,
                "help": self._cmd_help_cmd,
            }
        elif m == Mode.CONFIG_IF:
            base = {
                "ip": self._cmd_ip_if,
                "no": self._cmd_no_if,
                "shutdown": self._cmd_shutdown,
                "description": self._cmd_description,
                "switchport": self._cmd_switchport,
                "exit": self._cmd_exit_if,
                "end": self._cmd_end,
                "do": self._cmd_do,
                "help": self._cmd_help_cmd,
            }
        elif m == Mode.CONFIG_VLAN:
            base = {
                "name": self._cmd_vlan_name,
                "exit": self._cmd_exit_vlan,
                "end": self._cmd_end,
                "do": self._cmd_do,
                "help": self._cmd_help_cmd,
            }
        elif m == Mode.CONFIG_LINE:
            base = {
                "login": self._cmd_noop_ok,
                "password": self._cmd_noop_ok,
                "transport": self._cmd_noop_ok,
                "exit": self._cmd_exit_line,
                "end": self._cmd_end,
                "do": self._cmd_do,
                "help": self._cmd_help_cmd,
            }
        elif m == Mode.CONFIG_ROUTER:
            base = {
                "network": self._cmd_router_network,
                "router-id": self._cmd_noop_ok,
                "exit": self._cmd_exit_router,
                "end": self._cmd_end,
                "do": self._cmd_do,
                "help": self._cmd_help_cmd,
            }
        return base

    # -----/ Helpers /-----
    def _help(self, prefix: str) -> str:
        cmds = sorted(self._commands_for_mode().keys())
        if not prefix:
            rows = [f"  {c:<20}Exec commands" for c in cmds]
            return "\n".join(rows) + f"\n\n{self.prompt()}"
        # contextual
        parts = prefix.split()
        if not parts:
            return self._help("")
        # show ?
        if _abbrev_match("show", parts[0]) and len(parts) == 1:
            return (
                "  ip                     IP information\n"
                "  running-config         Current operating configuration\n"
                "  startup-config         Contents of startup configuration\n"
                "  interfaces             Interface status and configuration\n"
                "  version                System hardware and software status\n"
                "  vlan                   VTP VLAN status\n"
                f"\n{self.prompt()}{prefix}"
            )
        filtered = [c for c in cmds if c.startswith(parts[-1].lower()) or _abbrev_match(c, parts[-1])]
        if not filtered:
            return _invalid_input(prefix + "?", len(prefix))
        return "\n".join(f"  {c}" for c in filtered) + f"\n\n{self.prompt()}{prefix}"

    # -----/ USER / ENABLE commands /-----
    def _cmd_enable(self, args: list[str], line: str) -> str:
        self.mode = Mode.ENABLE
        return ""

    def _cmd_disable(self, args: list[str], line: str) -> str:
        self.mode = Mode.USER
        return ""

    def _cmd_exit_user(self, args: list[str], line: str) -> str:
        if self.mode == Mode.ENABLE:
            self.mode = Mode.USER
            return ""
        return "% Exit ignored in simulation (session stays open)."

    def _cmd_end(self, args: list[str], line: str) -> str:
        self.mode = Mode.ENABLE
        self._if_ctx = None
        self._vlan_ctx = None
        self._line_ctx = None
        self._router_ctx = None
        return ""

    def _cmd_configure(self, args: list[str], line: str) -> str:
        # configure terminal | conf t
        if not args:
            raise _CmdError("% Incomplete command.")
        if not (_abbrev_match("terminal", args[0]) or args[0].lower() in {"t", "term"}):
            # allow "configure terminal"
            joined = " ".join(args).lower()
            if not joined.startswith("t"):
                raise _CmdError(_invalid_input(line, line.lower().find(args[0])))
        self.mode = Mode.CONFIG
        return "Enter configuration commands, one per line.  End with CNTL/Z."

    def _cmd_terminal(self, args: list[str], line: str) -> str:
        return ""

    def _cmd_help_cmd(self, args: list[str], line: str) -> str:
        return self._help("")

    def _cmd_write(self, args: list[str], line: str) -> str:
        # write memory | write
        self.device.startup_config = self.device.running_config()
        return "Building configuration...\n[OK]"

    def _cmd_copy(self, args: list[str], line: str) -> str:
        # copy running-config startup-config
        joined = " ".join(args).lower().replace(" ", "")
        if "run" in joined and "start" in joined:
            self.device.startup_config = self.device.running_config()
            return "Destination filename [startup-config]? \nBuilding configuration...\n[OK]"
        if "start" in joined and "run" in joined:
            # restore
            return "% Not implemented: copy startup-config running-config (use conf t)."
        raise _CmdError("% Incomplete command.")

    def _cmd_clear(self, args: list[str], line: str) -> str:
        return ""

    def _cmd_reload(self, args: list[str], line: str) -> str:
        return "% Reload cancelled in simulation (would reboot device)."

    def _cmd_show_user(self, args: list[str], line: str) -> str:
        # limited show in user mode
        if not args:
            raise _CmdError("% Incomplete command.")
        if _abbrev_match("version", args[0]):
            return self.device.show_version()
        raise _CmdError("% Invalid input detected (privileged command). Try 'enable'.")

    def _cmd_show(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        a0 = args[0]
        if _abbrev_match("running-config", a0) or a0.lower() in {"run", "runn"}:
            return self.device.running_config()
        if _abbrev_match("startup-config", a0) or a0.lower().startswith("start"):
            return self.device.startup_config or "% Startup config empty. Use 'write memory'."
        if _abbrev_match("version", a0):
            return self.device.show_version()
        if _abbrev_match("vlan", a0):
            return self.device.show_vlan_brief()
        if _abbrev_match("interfaces", a0) or _abbrev_match("interface", a0):
            return self._show_interfaces(args[1:])
        if _abbrev_match("ip", a0):
            return self._show_ip(args[1:])
        if _abbrev_match("users", a0):
            return "    Line       User       Host(s)              Idle       Location\n"
        raise _CmdError(_invalid_input(line, line.lower().find(a0.lower())))

    def _show_ip(self, args: list[str]) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        if _abbrev_match("interface", args[0]) or _abbrev_match("interfaces", args[0]):
            rest = args[1:]
            if rest and _abbrev_match("brief", rest[0]):
                return self.device.show_ip_int_brief()
            return self.device.show_ip_int_brief()
        if _abbrev_match("route", args[0]):
            return self.device.show_ip_route()
        raise _CmdError("% Incomplete command.")

    def _show_interfaces(self, args: list[str]) -> str:
        names = list(self.device.interfaces)
        if args:
            resolved = self.device.resolve_if_name(args[0])
            if not resolved:
                raise _CmdError(f"% Invalid input detected: unknown interface {args[0]}")
            names = [resolved]
        blocks = []
        for n in sorted(names):
            iface = self.device.interfaces[n]
            st, proto = iface.status_pair()
            blocks.append(
                f"{n} is {st}, line protocol is {proto}\n"
                f"  Hardware is OpenIOS Simulated, address is aabb.cc00.0100\n"
                f"  Description: {iface.description or ''}\n"
                f"  Internet address is {iface.ip + '/' + str(_mask_prefix(iface.mask)) if iface.ip and iface.mask else 'unassigned'}\n"
                f"  MTU 1500 bytes, BW 1000000 Kbit/sec\n"
                f"  Encapsulation ARPA, loopback not set\n"
                f"  Last input never, output never, output hang never"
            )
        return "\n".join(blocks)

    def _cmd_ping(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        target = args[0]
        # Validate IP-ish
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
            # hostname not in DNS
            return (
                f"Translating \"{target}\"...domain server (255.255.255.255)\n"
                f"% Unrecognized host or address, or protocol not running."
            )
        if self.world is not None and hasattr(self.world, "ping"):
            return self.world.ping(self.device.name, target)  # type: ignore[attr-defined]
        # Local-only: success if target is on a connected up interface network
        return self._local_ping(target)

    def _local_ping(self, target: str) -> str:
        from ipaddress import IPv4Address, IPv4Interface

        try:
            dst = IPv4Address(target)
        except ValueError:
            return f"% Unrecognized host or address."
        for iface in self.device.interfaces.values():
            if not (iface.admin_up and iface.ip and iface.mask):
                continue
            try:
                net = IPv4Interface(f"{iface.ip}/{iface.mask}").network
            except ValueError:
                continue
            if dst in net:
                return _ping_success(target)
        return (
            f"Type escape sequence to abort.\n"
            f"Sending 5, 100-byte ICMP Echos to {target}, timeout is 2 seconds:\n"
            f".....\n"
            f"Success rate is 0 percent (0/5)"
        )

    def _cmd_traceroute(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        target = args[0]
        if self.world is not None and hasattr(self.world, "traceroute"):
            return self.world.traceroute(self.device.name, target)  # type: ignore[no-any-return]
        return (
            f"Type escape sequence to abort.\n"
            f"Tracing the route to {target}\n"
            f"  1  * * *\n"
            f"  2  * * *\n"
        )

    # -----/ CONFIG mode /-----
    def _cmd_hostname(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        name = args[0]
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9\-_]*$", name):
            raise _CmdError("% Invalid hostname.")
        self.device.hostname = name
        return ""

    def _cmd_interface(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        token = args[0]
        # interface GigabitEthernet 0/0  (split) → join
        if len(args) >= 2 and re.match(r"^\d", args[1]):
            token = args[0] + args[1]
        expanded = expand_interface_name(token)
        iface = self.device.get_iface(expanded)
        if iface is None:
            # Create on the fly for Loopback etc.
            if expanded.lower().startswith("loopback") or expanded.lower().startswith("vlan"):
                from openboson.netsim.ios.device import InterfaceState

                self.device.interfaces[expanded] = InterfaceState(name=expanded, admin_up=True)
                iface = self.device.interfaces[expanded]
            else:
                # Try fuzzy against existing
                resolved = self.device.resolve_if_name(token)
                if resolved is None:
                    raise _CmdError(
                        f"% Invalid input detected at '^' marker.\n"
                        f"{line}\n"
                        f"{'^'.rjust(line.find(args[0]) + 1)}\n"
                        f"% Unknown interface {token}"
                    )
                iface = self.device.interfaces[resolved]
                expanded = resolved
        self._if_ctx = iface.name
        self.mode = Mode.CONFIG_IF
        return ""

    def _cmd_vlan(self, args: list[str], line: str) -> str:
        if self.device.role not in (DeviceRole.SWITCH, DeviceRole.AP):
            # Routers may accept vlan only for SVI in some platforms — keep strict
            if self.device.role == DeviceRole.ROUTER:
                raise _CmdError("% Incomplete command / VLAN config requires switch platform.")
        if not args:
            raise _CmdError("% Incomplete command.")
        try:
            vid = int(args[0])
        except ValueError:
            raise _CmdError("% Invalid VLAN id.")
        if vid < 1 or vid > 4094:
            raise _CmdError("% VLAN id out of range (1-4094).")
        if vid not in self.device.vlans:
            self.device.vlans[vid] = f"VLAN{vid:04d}"
        self._vlan_ctx = vid
        self.mode = Mode.CONFIG_VLAN
        return ""

    def _cmd_ip_global(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        if _abbrev_match("route", args[0]):
            if len(args) < 4:
                raise _CmdError("% Incomplete command.")
            net, mask, nh = args[1], args[2], args[3]
            parsed = parse_ip_mask(net, mask)
            if not parsed:
                # net is network address; mask separate
                try:
                    from ipaddress import IPv4Address, IPv4Network

                    IPv4Address(net)
                    IPv4Network(f"0.0.0.0/{mask}")
                except ValueError:
                    raise _CmdError("% Invalid IP/mask.")
            self.device.static_routes.append(StaticRoute(network=net, mask=mask, next_hop=nh))
            return ""
        if _abbrev_match("domain-lookup", args[0]) or (
            len(args) >= 2 and args[0] == "domain" and "lookup" in args[1]
        ):
            return ""
        raise _CmdError("% Incomplete command.")

    def _cmd_no_global(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        if _abbrev_match("ip", args[0]) and len(args) >= 2 and _abbrev_match("domain-lookup", args[1]):
            return ""
        if _abbrev_match("ip", args[0]) and len(args) >= 2 and _abbrev_match("route", args[1]):
            # no ip route ...
            return ""
        return ""

    def _cmd_banner(self, args: list[str], line: str) -> str:
        # banner motd #text#
        if not args:
            raise _CmdError("% Incomplete command.")
        return "% Enter banner text (simulation stores simple motd)."

    def _cmd_line(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        self._line_ctx = " ".join(args)
        self.mode = Mode.CONFIG_LINE
        return ""

    def _cmd_router(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        if not _abbrev_match("ospf", args[0]) and args[0].lower() not in {"rip", "eigrp", "bgp"}:
            raise _CmdError("% Unknown routing process.")
        self._router_ctx = " ".join(args)
        self.mode = Mode.CONFIG_ROUTER
        self.device.extra_global.append(f"router {' '.join(args)}")
        return ""

    def _cmd_do(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        # Temporarily run as enable
        saved = self.mode
        self.mode = Mode.ENABLE
        try:
            res = self._dispatch(" ".join(args))
            return res.output
        finally:
            self.mode = saved

    def _cmd_exit_config(self, args: list[str], line: str) -> str:
        self.mode = Mode.ENABLE
        return ""

    # -----/ CONFIG-IF /-----
    def _cmd_ip_if(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        if not _abbrev_match("address", args[0]):
            raise _CmdError("% Incomplete command.")
        if len(args) < 3:
            # ip address 10.0.0.1/24
            if len(args) == 2 and "/" in args[1]:
                ip, _, pref = args[1].partition("/")
                parsed = parse_ip_mask(ip, pref)
                if not parsed:
                    raise _CmdError("% Invalid IP address or mask.")
                return self._set_if_ip(*parsed)
            raise _CmdError("% Incomplete command.")
        parsed = parse_ip_mask(args[1], args[2])
        if not parsed:
            raise _CmdError("% Invalid IP address or mask.")
        return self._set_if_ip(*parsed)

    def _set_if_ip(self, ip: str, mask: str) -> str:
        iface = self._require_if()
        if self.device.role == DeviceRole.SWITCH and iface.switchport_mode in {"access", "trunk"}:
            # L2 port — still allow for SVI-like training flexibility
            pass
        iface.ip = ip
        iface.mask = mask
        return ""

    def _cmd_no_if(self, args: list[str], line: str) -> str:
        if not args:
            raise _CmdError("% Incomplete command.")
        if _abbrev_match("shutdown", args[0]):
            iface = self._require_if()
            iface.admin_up = True
            iface.protocol_up = bool(iface.connected_to)
            return ""
        if _abbrev_match("ip", args[0]):
            iface = self._require_if()
            iface.ip = None
            iface.mask = None
            return ""
        return ""

    def _cmd_shutdown(self, args: list[str], line: str) -> str:
        iface = self._require_if()
        iface.admin_up = False
        iface.protocol_up = False
        return ""

    def _cmd_description(self, args: list[str], line: str) -> str:
        iface = self._require_if()
        iface.description = " ".join(args)
        return ""

    def _cmd_switchport(self, args: list[str], line: str) -> str:
        iface = self._require_if()
        if self.device.role not in (DeviceRole.SWITCH, DeviceRole.AP):
            raise _CmdError("% Switchport commands not supported on this platform.")
        if not args:
            raise _CmdError("% Incomplete command.")
        if _abbrev_match("mode", args[0]):
            if len(args) < 2:
                raise _CmdError("% Incomplete command.")
            mode = args[1].lower()
            if mode.startswith("trunk"):
                iface.switchport_mode = "trunk"
            elif mode.startswith("access"):
                iface.switchport_mode = "access"
                if iface.access_vlan is None:
                    iface.access_vlan = 1
            else:
                raise _CmdError("% Invalid switchport mode.")
            return ""
        if _abbrev_match("access", args[0]):
            if len(args) < 3 or not _abbrev_match("vlan", args[1]):
                raise _CmdError("% Incomplete command.")
            try:
                vid = int(args[2])
            except ValueError:
                raise _CmdError("% Invalid VLAN id.")
            iface.switchport_mode = "access"
            iface.access_vlan = vid
            if vid not in self.device.vlans:
                self.device.vlans[vid] = f"VLAN{vid:04d}"
            return ""
        if _abbrev_match("trunk", args[0]):
            # switchport trunk encapsulation dot1q
            iface.switchport_mode = "trunk"
            return ""
        raise _CmdError("% Incomplete command.")

    def _cmd_exit_if(self, args: list[str], line: str) -> str:
        self.mode = Mode.CONFIG
        self._if_ctx = None
        return ""

    def _require_if(self):
        if not self._if_ctx or self._if_ctx not in self.device.interfaces:
            raise _CmdError("% No interface context.")
        return self.device.interfaces[self._if_ctx]

    # -----/ VLAN /-----
    def _cmd_vlan_name(self, args: list[str], line: str) -> str:
        if not args or self._vlan_ctx is None:
            raise _CmdError("% Incomplete command.")
        self.device.vlans[self._vlan_ctx] = args[0]
        return ""

    def _cmd_exit_vlan(self, args: list[str], line: str) -> str:
        self.mode = Mode.CONFIG
        self._vlan_ctx = None
        return ""

    def _cmd_exit_line(self, args: list[str], line: str) -> str:
        self.mode = Mode.CONFIG
        self._line_ctx = None
        return ""

    def _cmd_exit_router(self, args: list[str], line: str) -> str:
        self.mode = Mode.CONFIG
        self._router_ctx = None
        return ""

    def _cmd_router_network(self, args: list[str], line: str) -> str:
        if len(args) < 1:
            raise _CmdError("% Incomplete command.")
        self.device.extra_global.append(f" network {' '.join(args)}")
        return ""

    def _cmd_noop_ok(self, args: list[str], line: str) -> str:
        return ""


class _CmdError(Exception):
    pass


def _tokenize(line: str) -> list[str]:
    # IOS is whitespace-split; keep it simple (no quoted strings needed for MVP).
    return line.strip().split()


def _abbrev_match(full: str, token: str) -> bool:
    """True if token is a unique-style prefix abbreviation of full."""
    f, t = full.lower(), token.lower()
    return f.startswith(t) and len(t) >= 1


def _resolve_command(token: str, commands: list[str]) -> str | None:
    t = token.lower()
    # exact
    for c in commands:
        if c == t:
            return c
    matches = [c for c in commands if c.startswith(t)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer longer common prefix uniqueness — still ambiguous
        return "__ambiguous__"
    # special: conf -> configure
    return None


def _invalid_input(line: str, caret_at: int) -> str:
    if caret_at < 0:
        caret_at = 0
    return (
        f"% Invalid input detected at '^' marker.\n"
        f"{line}\n"
        f"{' ' * caret_at}^\n"
    )


def _mask_prefix(mask: str | None) -> int:
    if not mask:
        return 0
    from openboson.netsim.ios.device import mask_to_prefix

    return mask_to_prefix(mask) or 0


def _ping_success(target: str) -> str:
    return (
        f"Type escape sequence to abort.\n"
        f"Sending 5, 100-byte ICMP Echos to {target}, timeout is 2 seconds:\n"
        f"!!!!!\n"
        f"Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/4 ms"
    )
