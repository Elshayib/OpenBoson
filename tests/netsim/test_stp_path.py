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
    assert "Success rate is 0 percent" in world.ping("PC1", "10.10.10.20")
    sw.feed("enable")
    sw.feed("configure terminal")
    sw.feed("interface GigabitEthernet0/1")
    sw.feed("spanning-tree portfast")
    sw.feed("interface GigabitEthernet0/2")
    sw.feed("spanning-tree portfast")
    sw.feed("end")
    assert "100 percent" in world.ping("PC1", "10.10.10.20")
    sw.feed("enable")
    sw.feed("configure terminal")
    sw.feed("interface GigabitEthernet0/1")
    sw.feed("no spanning-tree portfast")
    sw.feed("end")
    assert world.devices["SW1"].interfaces["GigabitEthernet0/1"].portfast is False
    assert "Success rate is 0 percent" in world.ping("PC1", "10.10.10.20")


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


def _shut_forwarding_member(world: LabWorld) -> None:
    """Shut the unbundled forwarding link (lowest local interface name)."""
    sh = world.shell("SW1")
    sh.feed("enable")
    sh.feed("configure terminal")
    sh.feed("interface GigabitEthernet0/1")
    sh.feed("shutdown")
    sh.feed("end")


def test_unbundled_parallel_links_block_redundant_path():
    lab = _ec_lab()
    world = LabWorld.from_lab(lab)
    _apply_pc_addrs(world, lab)
    _prep_access_and_portfast(world)
    assert "100 percent" in world.ping("PC1", "10.10.10.20")
    _shut_forwarding_member(world)
    assert "Success rate is 0 percent" in world.ping("PC1", "10.10.10.20")


def test_etherchannel_survives_one_member_shutdown():
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
        for ifname in ("GigabitEthernet0/1", "GigabitEthernet0/2"):
            assert world.devices[sw].interfaces[ifname].channel_group == 1
    _shut_forwarding_member(world)
    assert "100 percent" in world.ping("PC1", "10.10.10.20")
    sh = world.shell("SW1")
    sh.feed("enable")
    sh.feed("configure terminal")
    sh.feed("interface GigabitEthernet0/2")
    sh.feed("no channel-group")
    sh.feed("end")
    assert world.devices["SW1"].interfaces["GigabitEthernet0/2"].channel_group is None
