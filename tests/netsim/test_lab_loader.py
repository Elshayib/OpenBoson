"""Tests for NetSim lab schema + loader."""

from pathlib import Path

import pytest

from openboson.netsim.lab_loader import LabLoaderError, load_lab
from openboson.netsim.lab_schema import (
    DeviceType,
    LabBank,
    LabTask,
    Topology,
)


DEMO_LAB_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_basic_rtr_sw.yaml"


def test_demo_lab_loads():
    lab = load_lab(DEMO_LAB_PATH)
    assert isinstance(lab, LabBank)
    assert lab.lab_id == "ccna_basic_rtr_sw"
    assert lab.title.startswith("Configure Basic Router")


def test_demo_lab_topology_has_devices_and_links():
    lab = load_lab(DEMO_LAB_PATH)
    assert len(lab.topology.devices) == 2
    assert lab.device_names == ["R1", "SW1"]
    assert len(lab.topology.links) == 1
    link = lab.topology.links[0]
    assert link.a == "R1/GigabitEthernet0/0"
    assert link.b == "SW1/GigabitEthernet0/1"


def test_demo_lab_has_two_tasks_with_grading_rules():
    lab = load_lab(DEMO_LAB_PATH)
    assert len(lab.tasks) == 2
    for task in lab.tasks:
        assert task.grading_rules is not None
        assert task.grading_rules.require


def test_demo_lab_device_types():
    lab = load_lab(DEMO_LAB_PATH)
    types = {d.type for d in lab.topology.devices}
    assert DeviceType.ROUTER in types
    assert DeviceType.SWITCH in types


def test_invalid_lab_yaml_raises():
    # Missing required 'topic_code' -> validation error.
    bad = """
    title: x
    lab_id: y
    tasks: []
    """
    with pytest.raises(LabLoaderError):
        load_lab(bad)


def test_missing_lab_file_raises():
    with pytest.raises(LabLoaderError):
        load_lab("/no/such/lab.yaml")


def test_lab_with_no_topology_defaults():
    lab = LabBank(
        title="t", lab_id="id", topic_code="2.0", tasks=[LabTask(id="t1", instructions="do")]
    )
    assert isinstance(lab.topology, Topology)
    assert lab.topology.devices == []


def test_solution_config_optional():
    lab = LabBank(
        title="t",
        lab_id="id",
        topic_code="2.0",
        tasks=[LabTask(id="t1", instructions="do", expected_config="hostname X")],
    )
    assert lab.solution_config is None
