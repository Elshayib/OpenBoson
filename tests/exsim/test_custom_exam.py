"""Tests for custom exam filtering, sampling, and preset storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.exsim import custom_exam_store
from openboson.exsim.blueprint import InsufficientPoolError
from openboson.exsim.custom_exam import (
    CustomExamSpec,
    bank_from_custom,
    build_exam_from_custom,
    coverage_for_custom,
    filter_questions,
)
from openboson.stats_service import QuestionStat

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


@pytest.fixture
def pool_questions():
    return list(load_exam_bank(FIXTURE).questions)


def test_filter_by_cert_and_difficulty(pool_questions):
    spec = CustomExamSpec(cert="ccna", difficulties=[2], question_count=1)
    filtered = filter_questions(pool_questions, spec)
    assert filtered
    assert all(q.matches_cert("ccna") for q in filtered)
    assert all(int(q.difficulty) == 2 for q in filtered)


def test_filter_topic_prefix(pool_questions):
    codes = {q.topic_code for q in pool_questions}
    prefix = next(iter(codes)).split(".", 1)[0]
    spec = CustomExamSpec(cert="ccna", topic_codes=[prefix], question_count=1)
    filtered = filter_questions(pool_questions, spec)
    assert filtered
    assert all(q.topic_code == prefix or q.topic_code.startswith(prefix + ".") for q in filtered)


def test_history_missed_and_unseen(pool_questions):
    q0, q1 = pool_questions[0], pool_questions[1]
    history = {
        q0.id: QuestionStat(question_id=q0.id, seen=2, misses=1),
        q1.id: QuestionStat(question_id=q1.id, seen=1, misses=0),
    }
    missed = filter_questions(
        pool_questions,
        CustomExamSpec(cert="ccna", history="missed", question_count=1),
        history=history,
    )
    unseen = filter_questions(
        pool_questions,
        CustomExamSpec(cert="ccna", history="unseen", question_count=1),
        history=history,
    )
    assert q0.id in {q.id for q in missed}
    assert q1.id not in {q.id for q in missed}
    assert q0.id not in {q.id for q in unseen}
    assert q1.id not in {q.id for q in unseen}


def test_deterministic_seed(pool_questions):
    spec = CustomExamSpec(cert="ccna", question_count=3, seed=42)
    a = [q.id for q in build_exam_from_custom(pool_questions, spec)]
    b = [q.id for q in build_exam_from_custom(pool_questions, spec)]
    assert a == b
    other = CustomExamSpec(cert="ccna", question_count=3, seed=99)
    c = [q.id for q in build_exam_from_custom(pool_questions, other)]
    assert a != c


def test_insufficient_pool(pool_questions):
    spec = CustomExamSpec(cert="ccna", question_count=len(pool_questions) + 50)
    with pytest.raises(InsufficientPoolError) as exc:
        build_exam_from_custom(pool_questions, spec)
    assert exc.value.deficits.get("pool", 0) > 0


def test_coverage_and_bank(pool_questions):
    spec = CustomExamSpec(cert="ccna", question_count=2, title="Mini", time_limit_minutes=0)
    cov = coverage_for_custom(pool_questions, spec)
    assert cov["eligible"] >= 2
    assert cov["requested"] == 2
    qs = build_exam_from_custom(pool_questions, spec)
    bank = bank_from_custom(spec, qs)
    assert bank.code == "custom"
    assert bank.time_limit_minutes == 0
    assert len(bank.questions) == 2


def test_preset_store_round_trip(isolated_home):
    saved = custom_exam_store.save_preset(
        CustomExamSpec(
            title="My misses",
            cert="ccna",
            history="missed",
            question_count=10,
            seed=7,
            topic_codes=["3"],
            difficulties=[3, 4],
        )
    )
    assert saved.id
    loaded = custom_exam_store.get_preset(saved.id)
    assert loaded is not None
    assert loaded.title == "My misses"
    assert loaded.seed == 7
    assert loaded.topic_codes == ["3"]
    listed = custom_exam_store.list_presets()
    assert any(p.id == saved.id for p in listed)
    assert custom_exam_store.delete_preset(saved.id) is True
    assert custom_exam_store.get_preset(saved.id) is None
