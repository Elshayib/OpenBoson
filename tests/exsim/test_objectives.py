"""Tests for versioned exam objective registries."""

from __future__ import annotations

import pytest

from openboson.exsim.objectives import (
    CCNA_200_301_V1_1,
    ENCOR_350_401_V1_2,
    format_topic_label,
    get_allowed_objectives,
    invalid_topic_codes,
    objective_allowed,
)


def test_ccna_v11_known_objectives():
    allowed = get_allowed_objectives("200-301", "v1.1")
    assert allowed is not None
    assert "1.6" in allowed  # subnetting
    assert "1.9" in allowed  # IPv6 address types / anycast
    assert "1.5" in allowed  # TCP vs UDP
    assert "2.4" in allowed  # EtherChannel
    assert "2.5" in allowed  # Rapid PVST+
    assert "6.4" in allowed  # AI/ML
    assert allowed == CCNA_200_301_V1_1


def test_encor_v12_known_objectives():
    allowed = get_allowed_objectives("350-401", "v1.2")
    assert allowed is not None
    assert "1.4" in allowed
    assert "2.3" in allowed
    assert "3.1" in allowed and "3.2" in allowed and "3.3" in allowed
    assert "3.4" not in allowed  # v1.1 wireless / extra infra removed
    assert "2.4" not in allowed
    assert "6.7" in allowed
    assert allowed == ENCOR_350_401_V1_2


def test_pool_code_alias_resolves():
    assert get_allowed_objectives("pool-encor", "v1.2") == ENCOR_350_401_V1_2
    assert get_allowed_objectives("pool-ccna", "v1.1") == CCNA_200_301_V1_1


def test_invalid_topic_codes_reports_bad():
    bad = invalid_topic_codes(["1.1", "3.4", "9.9"], "350-401", "v1.2")
    assert "3.4" in bad
    assert "9.9" in bad
    assert "1.1" not in bad


def test_child_objective_allowed_under_leaf():
    allowed = ENCOR_350_401_V1_2
    assert objective_allowed("3.2.c", allowed)
    assert not objective_allowed("3.4.a", allowed)


def test_unknown_exam_raises_on_invalid_helper():
    with pytest.raises(KeyError):
        invalid_topic_codes(["1.1"], "999-999", "v1.0")


def test_format_topic_label_uses_title_not_code_echo():
    label = format_topic_label("1.1", cert="ccna", name="1.1")
    assert label.startswith("1.1 — ")
    assert "1.1 — 1.1" not in label
    assert "network components" in label.lower()
