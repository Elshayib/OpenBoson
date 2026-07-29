"""Tests for NetSim lab schema + loader."""

from pathlib import Path

import pytest

from openboson.netsim.lab_loader import LabLoaderError, load_lab
from openboson.netsim.lab_schema import DeviceType, LabBank


DEMO_LAB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "demo_labs"
    / "ccna_branch_office_access.yaml"
)


def test_demo_lab_loads():
    lab = load_lab(DEMO_LAB_PATH)
    assert isinstance(lab, LabBank)
    assert lab.lab_id == "ccna_branch_office_access"
    assert "Branch" in lab.title


def test_demo_lab_topology_has_four_devices():
    lab = load_lab(DEMO_LAB_PATH)
    assert len(lab.topology.devices) == 4
    assert set(lab.device_names) == {"R1", "SW1", "PC1", "PC2"}
    assert len(lab.topology.links) == 3


def test_demo_lab_tasks_objective_only_no_cli_babysitting():
    lab = load_lab(DEMO_LAB_PATH)
    assert len(lab.tasks) >= 3
    banned = ("configure terminal", "conf t", "no shutdown", "int g0/0", "`enable`")
    for task in lab.tasks:
        text = task.instructions.lower()
        for b in banned:
            assert b not in text, f"babysitting found in {task.id}: {b}"
        assert task.grading_rules is not None


def test_demo_lab_device_types():
    lab = load_lab(DEMO_LAB_PATH)
    types = {d.name: d.type for d in lab.topology.devices}
    assert types["R1"] == DeviceType.ROUTER
    assert types["SW1"] == DeviceType.SWITCH
    assert types["PC1"] == DeviceType.PC


def test_invalid_lab_yaml_raises():
    bad = """
    title: x
    lab_id: y
    tasks: []
    """
    with pytest.raises(LabLoaderError):
        load_lab(bad)
