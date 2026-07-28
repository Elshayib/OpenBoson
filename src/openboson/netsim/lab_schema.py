"""Pydantic v2 schemas for NetSim guided labs.

A lab bundles a topology (devices + links), a set of ordered tasks, and a
reference solution. The grader (``openboson.netsim.grader``) compares the
user's submitted configuration against each task's expected config.

Lab YAML shape::

    title: ...
    topic_code: "2.1"
    difficulty: 3
    objectives: [ ... ]
    topology:
      devices:
        - name: R1
          type: router
          interfaces: [GigabitEthernet0/0, GigabitEthernet0/1]
      links:
        - [R1, GigabitEthernet0/0, R2, GigabitEthernet0/0]
    tasks:
      - id: t1
        instructions: ...
        expected_config: |
          hostname R1
          ...
        grading_rules:
          require:
            - "hostname R1"
          forbid:
            - "no ip domain-lookup"
    solution_config: |
      ...
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeviceType(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    AP = "ap"
    FIREWALL = "firewall"
    PC = "pc"


class Interface(BaseModel):
    """A named interface on a device."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ip: str | None = None  # e.g. "10.0.0.1/24"
    connected_to: str | None = None  # "DeviceName/InterfaceName"
    description: str | None = None


class Device(BaseModel):
    """A network device in the lab topology."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: DeviceType = DeviceType.ROUTER
    interfaces: list[Interface] = Field(default_factory=list)


class Link(BaseModel):
    """A physical/logical link between two device interfaces."""

    model_config = ConfigDict(extra="forbid")

    a: str  # "DeviceName/InterfaceName"
    b: str  # "DeviceName/InterfaceName"


class Topology(BaseModel):
    """Devices + links describing the lab network."""

    model_config = ConfigDict(extra="forbid")

    devices: list[Device] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class GradingRule(BaseModel):
    """Per-task grading rules against the submitted configuration text."""

    model_config = ConfigDict(extra="forbid")

    require: list[str] = Field(default_factory=list)  # lines/commands that must be present
    forbid: list[str] = Field(default_factory=list)  # lines/commands that must NOT be present
    # Optional ordering requirement (e.g. OSPF network statements).
    require_order: list[str] = Field(default_factory=list)


class LabTask(BaseModel):
    """A single guided step in the lab."""

    model_config = ConfigDict(extra="forbid")

    id: str
    instructions: str
    expected_config: str | None = None
    grading_rules: GradingRule | None = None


class LabBank(BaseModel):
    """A complete guided lab definition."""

    model_config = ConfigDict(extra="forbid")

    title: str
    lab_id: str
    topic_code: str  # e.g. "2.1"
    difficulty: int = Field(default=3, ge=1, le=5)
    description: str | None = None
    objectives: list[str] = Field(default_factory=list)
    topology: Topology = Field(default_factory=Topology)
    tasks: list[LabTask] = Field(default_factory=list)
    solution_config: str | None = None

    @property
    def device_names(self) -> list[str]:
        return [d.name for d in self.topology.devices]
