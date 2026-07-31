"""Tests for exam blueprints and pool sampling."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank, load_question_pool
from openboson.exsim.blueprint import (
    InsufficientPoolError,
    allocate_counts,
    build_exam_from_blueprint,
    coverage_for_blueprint,
    get_blueprint,
)


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"
BANKS = Path(__file__).resolve().parents[2] / "data" / "demo_banks"


def test_allocate_counts_sums_to_total():
    bp = get_blueprint("ccna-200-301")
    counts = allocate_counts(100, bp.domain_weights)
    assert sum(counts.values()) == 100
    assert set(counts) == {d.prefix for d in bp.domain_weights}


def test_build_exam_from_full_pool():
    pool = load_question_pool(BANKS)
    bp = get_blueprint("ccna-200-301")
    qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(0))
    assert len(qs) == 100
    assert all(q.matches_cert("ccna") for q in qs)


def test_insufficient_pool_raises():
    bank = load_exam_bank(FIXTURE)
    bp = get_blueprint("ccna-200-301")
    with pytest.raises(InsufficientPoolError) as exc:
        build_exam_from_blueprint(bank.questions, bp, rng=random.Random(1))
    assert exc.value.deficits


def test_coverage_not_ready_for_fixture():
    bank = load_exam_bank(FIXTURE)
    bp = get_blueprint("ccna-200-301")
    cov = coverage_for_blueprint(bank.questions, bp)
    assert not cov.ready
    assert cov.deficits


def test_cert_filter_excludes_other_cert():
    pool = load_question_pool(BANKS)
    bp = get_blueprint("encor-350-401")
    qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(2))
    assert len(qs) == 100
    assert all(q.matches_cert("ccnp") for q in qs)
