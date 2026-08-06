"""Catalog quality gates for Labs Experience Rework."""

from __future__ import annotations

from pathlib import Path

import pytest

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.lab_schema import LabTier

ROOT = Path(__file__).resolve().parents[2]
LABS_DIR = ROOT / "data" / "demo_labs"


@pytest.fixture(scope="module")
def all_labs():
    labs = []
    for path in sorted(LABS_DIR.glob("*.yaml")):
        labs.append(load_lab(path))
    return labs


def test_bundled_lab_floor(all_labs):
    assert len(all_labs) >= 25


def test_gold_lab_floor(all_labs):
    gold = [lab for lab in all_labs if lab.lab_tier == LabTier.GOLD]
    assert len(gold) >= 20


def test_gold_labs_meet_authoring_gates(all_labs):
    for lab in all_labs:
        if lab.lab_tier != LabTier.GOLD:
            continue
        assert len(lab.topology.devices) >= 3, lab.lab_id
        assert len(lab.tasks) >= 3, lab.lab_id
        has_verify = any(
            t.verify is not None and (t.verify.ping or t.verify.show) for t in lab.tasks
        )
        assert has_verify, lab.lab_id


def test_encor_gold_wave(all_labs):
    encor = [
        lab
        for lab in all_labs
        if lab.lab_tier == LabTier.GOLD and "ccnp" in [t.lower() for t in lab.cert_tags]
    ]
    assert len(encor) >= 3


def test_branch_office_gold_preserved(all_labs):
    branch = next(lab for lab in all_labs if lab.lab_id == "ccna_branch_office_access")
    assert branch.lab_tier == LabTier.GOLD
    assert len(branch.topology.devices) == 4
    assert any(t.verify and t.verify.ping for t in branch.tasks)


def test_scale_campus_retained(all_labs):
    scale = next(lab for lab in all_labs if lab.lab_id == "ccna_scale_campus_10")
    assert scale.lab_tier == LabTier.SCALE
    assert len(scale.topology.devices) >= 10


def test_drills_are_badged(all_labs):
    drills = [lab for lab in all_labs if lab.lab_tier == LabTier.DRILL]
    assert len(drills) >= 1
