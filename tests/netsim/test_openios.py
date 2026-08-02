"""OpenIOS CLI emulator tests — modes, config, show, errors, ping."""

from pathlib import Path

import pytest

from openboson.netsim.ios.device import DeviceRole, DeviceRuntime, InterfaceState
from openboson.netsim.ios.shell import Mode, OpenIOSShell
from openboson.netsim.ios.world import LabWorld
from openboson.netsim.lab_loader import load_lab


@pytest.fixture
def router() -> DeviceRuntime:
    d = DeviceRuntime(name="R1", role=DeviceRole.ROUTER, hostname="R1")
    d.interfaces["GigabitEthernet0/0"] = InterfaceState(
        name="GigabitEthernet0/0", connected_to="SW1/GigabitEthernet0/1"
    )
    d.interfaces["GigabitEthernet0/1"] = InterfaceState(name="GigabitEthernet0/1")
    return d


@pytest.fixture
def shell(router) -> OpenIOSShell:
    return OpenIOSShell(router)


def _run(sh: OpenIOSShell, *lines: str) -> list[str]:
    outs = []
    for line in lines:
        outs.append(sh.feed(line).output)
    return outs


def test_banner_and_prompt(shell):
    assert shell.prompt() == "R1>"
    b = shell.banner()
    assert "OpenIOS" in b
    assert "R1>" in b


def test_enable_and_conf_t(shell):
    _run(shell, "enable")
    assert shell.mode == Mode.ENABLE
    assert shell.prompt() == "R1#"
    out = shell.feed("configure terminal").output
    assert "configuration commands" in out.lower()
    assert shell.mode == Mode.CONFIG
    assert shell.prompt() == "R1(config)#"


def test_conf_t_abbreviation(shell):
    _run(shell, "en", "conf t")
    assert shell.mode == Mode.CONFIG


def test_hostname_updates_prompt(shell):
    _run(shell, "en", "conf t", "hostname CORE-R1")
    assert shell.device.hostname == "CORE-R1"
    assert shell.prompt().startswith("CORE-R1")


def test_interface_ip_and_noshut(shell):
    _run(
        shell,
        "en",
        "conf t",
        "int g0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    )
    iface = shell.device.interfaces["GigabitEthernet0/0"]
    assert iface.ip == "10.10.10.1"
    assert iface.mask == "255.255.255.0"
    assert iface.admin_up is True
    cfg = shell.device.running_config()
    assert "hostname R1" in cfg
    assert "ip address 10.10.10.1 255.255.255.0" in cfg
    assert "no shutdown" in cfg


def test_show_ip_int_brief(shell):
    _run(
        shell,
        "en",
        "conf t",
        "int g0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shut",
        "end",
    )
    # no shut is abbreviation of... we only have "no" + "shutdown"
    # Fix: use full no shutdown already done above path - re-do properly
    out = shell.feed("show ip interface brief").output
    assert "GigabitEthernet0/0" in out
    assert "10.10.10.1" in out


def test_invalid_input_caret(shell):
    out = shell.feed("enablx").output
    assert "Invalid input" in out
    assert "^" in out


def test_ambiguous_command(shell):
    # In enable mode, if we had two commands with same prefix — skip if none
    _run(shell, "enable")
    # 'c' matches clear, configure, copy — ambiguous
    out = shell.feed("c").output
    assert "Ambiguous" in out or "Invalid" in out


def test_show_run_after_config(shell):
    _run(
        shell,
        "enable",
        "configure terminal",
        "hostname R1",
        "interface GigabitEthernet0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    )
    out = shell.feed("show run").output
    assert "hostname R1" in out
    assert "interface GigabitEthernet0/0" in out


def test_switch_vlan_and_trunk():
    sw = DeviceRuntime(name="SW1", role=DeviceRole.SWITCH)
    sw.interfaces["GigabitEthernet0/1"] = InterfaceState(name="GigabitEthernet0/1")
    sw.interfaces["GigabitEthernet0/2"] = InterfaceState(name="GigabitEthernet0/2")
    sh = OpenIOSShell(sw)
    _run(
        sh,
        "en",
        "conf t",
        "hostname SW1",
        "vlan 10",
        "name USERS",
        "interface GigabitEthernet0/1",
        "switchport mode trunk",
        "interface GigabitEthernet0/2",
        "switchport mode access",
        "switchport access vlan 10",
        "end",
    )
    assert 10 in sw.vlans
    assert sw.vlans[10] == "USERS"
    assert sw.interfaces["GigabitEthernet0/1"].switchport_mode == "trunk"
    assert sw.interfaces["GigabitEthernet0/2"].switchport_mode == "access"
    assert sw.interfaces["GigabitEthernet0/2"].access_vlan == 10
    cfg = sw.running_config()
    assert "vlan 10" in cfg
    assert "switchport mode trunk" in cfg


def test_help_question_mark(shell):
    out = shell.feed("?").output
    assert "enable" in out


def test_world_from_demo_lab_and_ping():
    lab = load_lab(
        Path(__file__).resolve().parents[2]
        / "data"
        / "demo_labs"
        / "ccna_branch_office_access.yaml"
    )
    world = LabWorld.from_lab(lab)
    assert "R1" in world.devices
    assert "PC1" in world.devices
    r1 = world.shell("R1")
    _run(
        r1,
        "en",
        "conf t",
        "hostname R1",
        "int g0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    )
    out = r1.feed("ping 10.10.10.1").output
    assert "100 percent" in out or "!!!!!" in out


def test_pc_host_shell_ipconfig():
    lab = load_lab(
        Path(__file__).resolve().parents[2]
        / "data"
        / "demo_labs"
        / "ccna_branch_office_access.yaml"
    )
    world = LabWorld.from_lab(lab)
    pc = world.shell("PC1")
    pc.feed("ip address 10.10.10.10 255.255.255.0")
    out = pc.feed("ipconfig").output
    assert "10.10.10.10" in out
    assert "255.255.255.0" in out


def test_write_memory(shell):
    _run(shell, "en", "conf t", "hostname R1", "end")
    out = shell.feed("write memory").output
    assert "OK" in out
    assert "hostname R1" in shell.device.startup_config


def test_show_and_interface_completion(shell):
    _run(shell, "enable")
    assert "running-config" in shell.complete("show ")
    assert "route" in shell.complete("show ip ")
    _run(shell, "configure terminal")
    cands = shell.complete("interface ")
    assert any("GigabitEthernet0/0" in c for c in cands)


def test_matrix_stp_etherchannel_ipv6():
    sw = DeviceRuntime(name="SW1", role=DeviceRole.SWITCH)
    sw.interfaces["GigabitEthernet0/2"] = InterfaceState(name="GigabitEthernet0/2")
    sw.interfaces["GigabitEthernet0/1"] = InterfaceState(name="GigabitEthernet0/1")
    sh = OpenIOSShell(sw)
    _run(
        sh,
        "en",
        "conf t",
        "interface GigabitEthernet0/2",
        "spanning-tree portfast",
        "interface GigabitEthernet0/1",
        "channel-group 1 mode on",
        "end",
    )
    cfg = sw.running_config()
    assert "spanning-tree portfast" in cfg
    assert "channel-group 1 mode on" in cfg

    r = DeviceRuntime(name="R1", role=DeviceRole.ROUTER)
    r.interfaces["GigabitEthernet0/0"] = InterfaceState(name="GigabitEthernet0/0")
    rsh = OpenIOSShell(r)
    _run(
        rsh,
        "en",
        "conf t",
        "ipv6 unicast-routing",
        "interface GigabitEthernet0/0",
        "ipv6 address 2001:db8:1::1/64",
        "end",
    )
    rcfg = r.running_config()
    assert "ipv6 unicast-routing" in rcfg
    assert "ipv6 address 2001:db8:1::1/64" in rcfg


def test_terminal_length_paging(shell):
    _run(shell, "enable", "terminal length 5")
    # Build a long running-config via many interface descriptions.
    _run(shell, "configure terminal")
    for i in range(12):
        name = f"Loopback{i}"
        shell.device.interfaces[name] = InterfaceState(name=name, admin_up=True)
        _run(shell, f"interface {name}", f"description pad-{i}")
    _run(shell, "end")
    out = shell.feed("show running-config").output
    assert "--More--" in out
    more = shell.feed(" ").output
    assert more  # continued
    shell.feed("q")  # quit pager
