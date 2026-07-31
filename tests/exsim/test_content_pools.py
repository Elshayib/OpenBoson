"""Content integrity tests for demo question pools and generator."""

from __future__ import annotations

import importlib.util
import random
from collections import Counter
from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank, load_question_pool
from openboson.exsim.blueprint import (
    allocate_counts,
    build_exam_from_blueprint,
    coverage_for_blueprint,
    get_blueprint,
)
from openboson.exsim.objectives import invalid_topic_codes

ROOT = Path(__file__).resolve().parents[2]
BANKS = ROOT / "data" / "demo_banks"
GENERATOR = ROOT / "scripts" / "generate_question_pools.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_question_pools", GENERATOR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ccna_bank():
    return load_exam_bank(BANKS / "pool_ccna.yaml")


@pytest.fixture(scope="module")
def encor_bank():
    return load_exam_bank(BANKS / "pool_encor.yaml")


def test_ccna_pool_metadata(ccna_bank):
    assert ccna_bank.version == "v1.1"
    assert ccna_bank.code == "pool-ccna"
    assert all(q.matches_cert("ccna") for q in ccna_bank.questions)


def test_encor_pool_metadata(encor_bank):
    assert encor_bank.version == "v1.2"
    assert encor_bank.code == "pool-encor"
    assert all(q.matches_cert("ccnp") for q in encor_bank.questions)


def test_unique_question_ids(ccna_bank, encor_bank):
    ids = [q.id for q in ccna_bank.questions] + [q.id for q in encor_bank.questions]
    assert len(ids) == len(set(ids))


def test_ccna_objectives_valid(ccna_bank):
    bad = invalid_topic_codes((q.topic_code for q in ccna_bank.questions), "200-301", "v1.1")
    assert bad == []


def test_encor_objectives_valid(encor_bank):
    bad = invalid_topic_codes((q.topic_code for q in encor_bank.questions), "350-401", "v1.2")
    assert bad == []


def test_questions_have_explanations_and_references(ccna_bank, encor_bank):
    for q in (*ccna_bank.questions, *encor_bank.questions):
        assert q.explanation and q.explanation.strip()
        assert q.references, f"{q.id} missing references"


def test_answer_refs_resolve(ccna_bank, encor_bank):
    for q in (*ccna_bank.questions, *encor_bank.questions):
        correct = q.correct_answer_model
        if q.type.value in ("single_choice", "multiple_choice"):
            choice_ids = {c.id for c in (q.choices or [])}
            if q.type.value == "single_choice":
                assert correct.answer in choice_ids, q.id
            else:
                assert set(correct.answers) <= choice_ids, q.id
        elif q.type.value == "ordered_list":
            assert set(correct.order) == set(q.ordered_items or []), q.id
        elif q.type.value == "drag_match":
            pairs = {(p.left, p.right) for p in (q.drag_pairs or [])}
            correct_pairs = {(p.left, p.right) for p in correct.pairs}
            assert pairs == correct_pairs, q.id


def _domain_counts(questions) -> dict[str, int]:
    return Counter(q.topic_code.split(".", 1)[0] for q in questions)


def test_ccna_domain_capacity_exceeds_quota(ccna_bank):
    bp = get_blueprint("ccna-200-301")
    required = allocate_counts(bp.question_count, bp.domain_weights)
    counts = _domain_counts(ccna_bank.questions)
    for domain, need in required.items():
        assert counts.get(domain, 0) > need, (
            f"CCNA domain {domain}: {counts.get(domain, 0)} <= {need}"
        )


def test_encor_domain_capacity_exceeds_quota(encor_bank):
    bp = get_blueprint("encor-350-401")
    required = allocate_counts(bp.question_count, bp.domain_weights)
    counts = _domain_counts(encor_bank.questions)
    for domain, need in required.items():
        assert counts.get(domain, 0) > need, (
            f"ENCOR domain {domain}: {counts.get(domain, 0)} <= {need}"
        )


def test_encor_blueprint_weights_and_version():
    bp = get_blueprint("encor-350-401")
    assert bp.version == "v1.2"
    weights = {d.prefix: d.weight for d in bp.domain_weights}
    assert weights == {
        "1": 0.15,
        "2": 0.10,
        "3": 0.30,
        "4": 0.10,
        "5": 0.20,
        "6": 0.15,
    }
    assert bp.domain_weights[5].name == "Automation and Artificial Intelligence"
    counts = allocate_counts(100, bp.domain_weights)
    assert counts == {"1": 15, "2": 10, "3": 30, "4": 10, "5": 20, "6": 15}


def test_bank_from_blueprint_uses_version():
    from openboson.exsim.blueprint import bank_from_blueprint

    bp = get_blueprint("encor-350-401")
    pool = load_question_pool(BANKS)
    qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(0))
    bank = bank_from_blueprint(bp, qs)
    assert bank.version == "v1.2"
    assert bank.code == "350-401"


def test_encor_3_090_bgp_order(encor_bank):
    q = next(q for q in encor_bank.questions if q.id == "encor-3-090")
    assert q.topic_code == "3.2"
    assert q.correct_answer_model.order == [
        "Weight (Cisco highest)",
        "Highest Local Preference",
        "Lowest MED (same AS)",
        "Prefer eBGP over iBGP",
    ]


def test_known_ccna_retags(ccna_bank):
    by_id = {q.id: q for q in ccna_bank.questions}
    assert by_id["ccna-1-001"].topic_code == "1.6"  # subnetting
    assert by_id["ccna-1-005"].topic_code == "1.5"  # TCP
    assert by_id["ccna-1-006"].topic_code == "1.9"  # anycast
    assert by_id["ccna-1-008"].topic_code == "1.5"  # UDP
    assert by_id["ccna-2-002"].topic_code == "2.5"  # Rapid PVST+
    assert by_id["ccna-2-003"].topic_code == "2.4"  # EtherChannel


def test_generator_deterministic():
    mod = _load_generator()
    a = mod.build_ccna()
    b = mod.build_ccna()
    assert [q["id"] for q in a] == [q["id"] for q in b]
    assert [q["topic_code"] for q in a] == [q["topic_code"] for q in b]
    c = mod.build_encor()
    d = mod.build_encor()
    assert [q["id"] for q in c] == [q["id"] for q in d]
    q090 = next(q for q in c if q["id"] == "encor-3-090")
    assert q090["correct"]["order"][2] == "Lowest MED (same AS)"


def test_full_pool_coverage_ready():
    pool = load_question_pool(BANKS)
    for bp_id in ("ccna-200-301", "encor-350-401"):
        bp = get_blueprint(bp_id)
        cov = coverage_for_blueprint(pool.questions, bp)
        assert cov.ready, cov.deficits
        qs = build_exam_from_blueprint(pool.questions, bp, rng=random.Random(42))
        assert len(qs) == 100


def test_release_content_volume_gates():
    ccna = load_exam_bank(BANKS / "pool_ccna.yaml")
    encor = load_exam_bank(BANKS / "pool_encor.yaml")
    assert len(ccna.questions) >= 500
    assert len(encor.questions) >= 400
    for bank in (ccna, encor):
        non_sc = sum(1 for q in bank.questions if q.type.value != "single_choice")
        assert non_sc / len(bank.questions) >= 0.15


def test_lab_catalog_count():
    labs = list((ROOT / "data" / "demo_labs").glob("*.yaml"))
    assert len(labs) >= 20
