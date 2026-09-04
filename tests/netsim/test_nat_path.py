"""NAT overload must be required for inside-host to outside-peer ping."""

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
    assert "Success rate is 0 percent" in result
