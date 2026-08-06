"""Pydantic v2 schemas for NetSim guided labs.

A lab bundles a topology (devices + links), ordered tasks, optional verify
blocks, and a reference solution. The grader compares live OpenIOS state and
submitted configuration against per-device requirements.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeviceType(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    AP = "ap"
    FIREWALL = "firewall"
    PC = "pc"


class LabTier(str, Enum):
    """Catalog presentation + authoring gate.

    - ``gold``: multi-device scenario with behavioral verify (default new labs)
    - ``drill``: CLI/config practice; may be single-device; never sold as NetSim
    - ``scale``: topology/perf gate labs (e.g. 10-device campus)
    """

    GOLD = "gold"
    DRILL = "drill"
    SCALE = "scale"


class Interface(BaseModel):
    """A named interface on a device."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ip: str | None = None
    connected_to: str | None = None
    description: str | None = None


class Device(BaseModel):
    """A network device in the lab topology."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: DeviceType = DeviceType.ROUTER
    interfaces: list[Interface] = Field(default_factory=list)
    base_config: str | None = None
    x: float | None = None
    y: float | None = None


class Link(BaseModel):
    """A physical/logical link between two device interfaces."""

    model_config = ConfigDict(extra="forbid")

    a: str
    b: str


class Topology(BaseModel):
    """Devices + links describing the lab network."""

    model_config = ConfigDict(extra="forbid")

    devices: list[Device] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class GradingRule(BaseModel):
    """Per-task grading rules against configuration text."""

    model_config = ConfigDict(extra="forbid")

    require: list[str] = Field(default_factory=list)
    forbid: list[str] = Field(default_factory=list)
    require_order: list[str] = Field(default_factory=list)
    # When set, only this device's running-config is graded.
    device: str | None = None
    weight: float = Field(default=1.0, ge=0.0)


class VerifyPing(BaseModel):
    """Reachability assertion evaluated against LabWorld.ping."""

    model_config = ConfigDict(extra="forbid")

    source: str
    destination: str
    should_succeed: bool = True


class VerifyShow(BaseModel):
    """Assert a substring appears in a device show/running output."""

    model_config = ConfigDict(extra="forbid")

    device: str
    contains: list[str] = Field(default_factory=list)
    command: str | None = None  # informational; evaluator uses running-config by default


class VerifyBlock(BaseModel):
    """Non-config assertions for a task."""

    model_config = ConfigDict(extra="forbid")

    ping: list[VerifyPing] = Field(default_factory=list)
    show: list[VerifyShow] = Field(default_factory=list)


class LabTask(BaseModel):
    """A single guided step in the lab."""

    model_config = ConfigDict(extra="forbid")

    id: str
    instructions: str
    expected_config: str | None = None
    grading_rules: GradingRule | None = None
    verify: VerifyBlock | None = None
    weight: float = Field(default=1.0, ge=0.0)


class LabBank(BaseModel):
    """A complete guided lab definition."""

    model_config = ConfigDict(extra="forbid")

    title: str
    lab_id: str
    topic_code: str
    difficulty: int = Field(default=3, ge=1, le=5)
    description: str | None = None
    objectives: list[str] = Field(default_factory=list)
    topology: Topology = Field(default_factory=Topology)
    tasks: list[LabTask] = Field(default_factory=list)
    solution_config: str | None = None
    schema_version: int = 1
    cert_tags: list[str] = Field(default_factory=lambda: ["ccna"])
    pass_threshold: float = Field(default=1.0, ge=0.0, le=1.0)
    session_seed: int | None = None
    lab_tier: LabTier = LabTier.DRILL

    @property
    def device_names(self) -> list[str]:
        return [d.name for d in self.topology.devices]

    @property
    def is_gold(self) -> bool:
        return self.lab_tier == LabTier.GOLD

    @model_validator(mode="after")
    def _validate_limits(self) -> LabBank:
        devices = self.topology.devices
        if len(devices) > 50:
            raise ValueError("Lab exceeds maximum of 50 devices")
        if len(self.tasks) > 200:
            raise ValueError("Lab exceeds maximum of 200 tasks")
        names = [d.name for d in devices]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate device names in topology")
        if self.lab_tier == LabTier.GOLD:
            if len(devices) < 3:
                raise ValueError("Gold labs require at least 3 devices")
            if len(self.tasks) < 3:
                raise ValueError("Gold labs require at least 3 tasks")
            has_verify = any(
                t.verify is not None and (t.verify.ping or t.verify.show) for t in self.tasks
            )
            if not has_verify:
                raise ValueError("Gold labs require verify.ping and/or verify.show")
        return self
