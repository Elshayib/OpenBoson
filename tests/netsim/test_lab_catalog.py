"""Tests for NetSim lab catalog filtering."""

from __future__ import annotations

from openboson.netsim.lab_catalog import filter_labs
from openboson.netsim.lab_schema import LabBank, Topology


def _lab(**kwargs) -> LabBank:
    base = {
        "title": "Sample",
        "lab_id": "sample",
        "topic_code": "2.1",
        "difficulty": 2,
        "description": "VLAN trunking basics",
        "objectives": ["Configure access VLANs"],
        "topology": Topology(),
        "tasks": [],
        "cert_tags": ["ccna"],
    }
    base.update(kwargs)
    return LabBank.model_validate(base)


def test_filter_by_topic_prefix_and_difficulty():
    labs = [
        _lab(lab_id="a", topic_code="2.1", difficulty=2, title="VLANs"),
        _lab(lab_id="b", topic_code="2.4", difficulty=3, title="STP"),
        _lab(lab_id="c", topic_code="3.1", difficulty=2, title="Static routes"),
    ]
    assert [x.lab_id for x in filter_labs(labs, topic_code="2")] == ["a", "b"]
    assert [x.lab_id for x in filter_labs(labs, difficulty=2)] == ["a", "c"]
    assert [x.lab_id for x in filter_labs(labs, topic_code="2", difficulty=3)] == ["b"]


def test_filter_text_and_cert():
    labs = [
        _lab(lab_id="a", title="ACL basics", description="Filter traffic", objectives=["ACL"]),
        _lab(
            lab_id="b",
            title="OSPF single area",
            description="Routing",
            cert_tags=["ccnp"],
            topic_code="3.2",
        ),
    ]
    assert [x.lab_id for x in filter_labs(labs, q="acl")] == ["a"]
    assert [x.lab_id for x in filter_labs(labs, cert="ccnp")] == ["b"]
    assert filter_labs(labs, q="missing") == []
