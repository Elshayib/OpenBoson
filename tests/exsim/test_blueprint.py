"""Tests for exam blueprints and pool sampling."""

from __future__ import annotations

import random
from collections import Counter
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
from openboson.exsim.session import ExamSession

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"
BANKS = Path(__file__).resolve().parents[2] / "data" / "demo_banks"


def test_allocate_counts_sums_to_total():
    bp = get_blueprint("ccna-200-301")
    counts = allocate_counts(100, bp.domain_weights)
    assert sum(counts.values()) == 100
    assert set(counts) == {d.prefix for d in bp.domain_weights}
    # Exact official-ish quotas for 100 questions / published weights.
    assert counts == {"1": 20, "2": 20, "3": 25, "4": 10, "5": 15, "6": 10}


def test_build_exam_from_full_pool():
    pool = load_question_pool(BANKS)
    bp = get_blueprint("ccna-200-301")
    qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(0))
    assert len(qs) == 100
    assert all(q.matches_cert("ccna") for q in qs)
    expected = allocate_counts(bp.question_count, bp.domain_weights)
    actual = Counter(q.topic_code.split(".", 1)[0] for q in qs)
    assert dict(actual) == expected


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


def test_encor_exact_domain_quotas():
    pool = load_question_pool(BANKS)
    bp = get_blueprint("encor-350-401")
    assert bp.version == "v1.2"
    required = allocate_counts(100, bp.domain_weights)
    assert required == {"1": 15, "2": 10, "3": 30, "4": 10, "5": 20, "6": 15}
    qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(3))
    got = Counter(q.topic_code.split(".", 1)[0] for q in qs)
    assert dict(got) == required


def test_ccna_exact_domain_quotas():
    pool = load_question_pool(BANKS)
    bp = get_blueprint("ccna-200-301")
    assert bp.version == "v1.1"
    required = allocate_counts(100, bp.domain_weights)
    assert sum(required.values()) == 100
    qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(4))
    got = Counter(q.topic_code.split(".", 1)[0] for q in qs)
    assert dict(got) == required
    assert all(q.matches_cert("ccna") for q in qs)


def test_empty_subset_raises_insufficient_pool():
    bank = load_exam_bank(FIXTURE)
    with pytest.raises(InsufficientPoolError, match="empty question set"):
        ExamSession.create(bank, questions=[])


def test_empty_subset_does_not_expand_to_full_bank():
    bank = load_exam_bank(FIXTURE)
    try:
        ExamSession.create(bank, questions=[])
        raised = False
    except InsufficientPoolError:
        raised = True
    assert raised
    # Full-bank path still works when questions is omitted.
    session = ExamSession.create(bank, shuffle=False)
    assert len(session.questions) == len(bank.questions)
