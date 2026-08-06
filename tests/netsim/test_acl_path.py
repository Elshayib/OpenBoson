"""ACL path filtering and verify coaching hints."""

from __future__ import annotations

from openboson.netsim.grader import evaluate_verify
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
    VerifyBlock,
    VerifyPing,
)


def _acl_lab() -> LabBank:
    return LabBank(
        title="ACL path",
        lab_id="test_acl_path",
        topic_code="5.1",
        lab_tier=LabTier.DRILL,
        topology=Topology(
            devices=[
                Device(
                    name="R1",
                    type=DeviceType.ROUTER,
                    interfaces=[
                        Interface(name="GigabitEthernet0/0", ip="10.0.0.1/24"),
                        Interface(name="GigabitEthernet0/1", ip="10.0.1.1/24"),
                    ],
                    base_config=(
                        "interface GigabitEthernet0/0\n"
                        " ip address 10.0.0.1 255.255.255.0\n"
                        " no shutdown\n"
                        "interface GigabitEthernet0/1\n"
                        " ip address 10.0.1.1 255.255.255.0\n"
                        " no shutdown\n"
                    ),
                ),
                Device(
                    name="PC1",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="10.0.0.10/24")],
                    base_config="ip address 10.0.0.10 255.255.255.0\n",
                ),
                Device(
                    name="PC2",
                    type=DeviceType.PC,
                    interfaces=[Interface(name="eth0", ip="10.0.1.10/24")],
                    base_config="ip address 10.0.1.10 255.255.255.0\n",
                ),
            ],
            links=[
                Link(a="R1/GigabitEthernet0/0", b="PC1/eth0"),
                Link(a="R1/GigabitEthernet0/1", b="PC2/eth0"),
            ],
        ),
        tasks=[
            LabTask(
                id="t1",
                instructions="ACL",
                verify=VerifyBlock(
                    ping=[VerifyPing(source="PC1", destination="10.0.1.10", should_succeed=False)]
                ),
            )
        ],
    )


def _apply_base(world: LabWorld, lab: LabBank) -> None:
    for d in lab.topology.devices:
        cfg = (d.base_config or "").strip()
        if not cfg:
            continue
        shell = world.shell(d.name)
        if d.type == DeviceType.PC:
            for line in cfg.splitlines():
                if line.strip():
                    shell.feed(line.strip())
        else:
            shell.feed("enable")
            shell.feed("configure terminal")
            for line in cfg.splitlines():
                if line.strip():
                    shell.feed(line.strip())
            shell.feed("end")


def test_acl_denies_icmp_across_router():
    lab = _acl_lab()
    world = LabWorld.from_lab(lab)
    _apply_base(world, lab)
    r1 = world.shell("R1")
    r1.feed("enable")
    r1.feed("configure terminal")
    r1.feed("access-list 100 deny icmp any host 10.0.1.10")
    r1.feed("access-list 100 permit ip any any")
    r1.feed("interface GigabitEthernet0/0")
    r1.feed("ip access-group 100 in")
    r1.feed("end")
    assert "0 percent" in world.ping("PC1", "10.0.1.10")
    assert "access list" in world.explain_unreachable("PC1", "10.0.1.10").lower()


def test_verify_includes_unreachable_hint():
    lab = _acl_lab()
    world = LabWorld.from_lab(lab)
    failures = evaluate_verify(
        VerifyBlock(ping=[VerifyPing(source="PC1", destination="10.0.1.10", should_succeed=True)]),
        world,
    )
    assert failures
    assert any("Reachability" in f for f in failures)
