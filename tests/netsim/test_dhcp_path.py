"""DHCP pool must assign a PC address before ping works."""

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


def _dhcp_lab() -> LabBank:
    return LabBank(
        title="DHCP path",
        lab_id="test_dhcp_path",
        topic_code="4.3",
        lab_tier=LabTier.DRILL,
        topology=Topology(
            devices=[
                Device(
                    name="R1",
                    type=DeviceType.ROUTER,
                    interfaces=[Interface(name="GigabitEthernet0/0")],
                ),
                Device(
                    name="PC1",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0")],
                ),
            ],
            links=[Link(a="R1/GigabitEthernet0/0", b="PC1/eth0")],
        ),
        tasks=[LabTask(id="t1", instructions="DHCP")],
    )


def _prep_router(world: LabWorld) -> None:
    r1 = world.shell("R1")
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 192.168.10.1 255.255.255.0",
        "no shutdown",
        "exit",
        "ip dhcp pool LAN",
        "network 192.168.10.0 255.255.255.0",
        "default-router 192.168.10.1",
        "exit",
        "ip dhcp excluded-address 192.168.10.1 192.168.10.10",
        "end",
    ):
        r1.feed(line)


def test_pc_without_address_cannot_ping_gateway():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    _prep_router(world)
    result = world.ping("PC1", "192.168.10.1")
    assert "0 percent" in result


def test_ipconfig_renew_assigns_pool_address_and_ping_works():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    _prep_router(world)
    out = world.shell("PC1").feed("ipconfig /renew")
    text = out.output if hasattr(out, "output") else str(out)
    iface = world.devices["PC1"].interfaces["eth0"]
    assert iface.ip is not None
    assert iface.ip.startswith("192.168.10.")
    assert iface.ip != "192.168.10.1"
    # excluded 1–10, so first assignable is .11
    assert iface.ip == "192.168.10.11"
    result = world.ping("PC1", "192.168.10.1")
    assert "100 percent" in result
    assert "192.168.10.11" in text or "renew" in text.lower() or iface.ip in text


def test_renew_without_pool_leaves_pc_unaddressed():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    r1 = world.shell("R1")
    for line in (
        "enable",
        "configure terminal",
        "interface GigabitEthernet0/0",
        "ip address 192.168.10.1 255.255.255.0",
        "no shutdown",
        "end",
    ):
        r1.feed(line)
    world.shell("PC1").feed("ipconfig /renew")
    assert world.devices["PC1"].interfaces["eth0"].ip is None


def test_dhcp_pool_renders_in_running_config():
    lab = _dhcp_lab()
    world = LabWorld.from_lab(lab)
    _prep_router(world)
    cfg = world.devices["R1"].running_config().lower()
    assert "ip dhcp pool lan" in cfg
    assert "network 192.168.10.0 255.255.255.0" in cfg
    assert "default-router 192.168.10.1" in cfg
