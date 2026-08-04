"""Tests for question-bank schema and loader."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from openboson.bank_loader import (
    BankLoaderError,
    load_banks_detailed,
    load_exam_bank,
    load_question_pool,
)
from openboson.bank_schema import (
    DragMatchAnswer,
    ExamBank,
    MultipleChoiceAnswer,
    OrderedListAnswer,
    QuestionType,
    SimAnswer,
    SingleChoiceAnswer,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_bank.yaml"
BANKS_DIR = Path(__file__).resolve().parents[1] / "data" / "demo_banks"


def test_fixture_bank_loads_from_file():
    bank = load_exam_bank(FIXTURE_PATH)
    assert isinstance(bank, ExamBank)
    assert bank.code == "fixture-200-301"
    assert bank.schema_version >= 1
    assert len(bank.questions) == 6
    assert all(q.cert_tags for q in bank.questions)


def test_fixture_bank_covers_all_six_domains():
    bank = load_exam_bank(FIXTURE_PATH)
    prefixes = {q.topic_code.split(".")[0] + ".0" for q in bank.questions}
    assert prefixes == {"1.0", "2.0", "3.0", "4.0", "5.0", "6.0"}


def test_merged_pool_loads():
    pool = load_question_pool(BANKS_DIR)
    assert len(pool.questions) >= 200


@pytest.mark.parametrize(
    "qtype,model_cls",
    [
        (QuestionType.SINGLE_CHOICE, SingleChoiceAnswer),
        (QuestionType.MULTIPLE_CHOICE, MultipleChoiceAnswer),
        (QuestionType.DRAG_MATCH, DragMatchAnswer),
        (QuestionType.ORDERED_LIST, OrderedListAnswer),
        (QuestionType.SIM, SimAnswer),
    ],
)
def test_correct_answer_model_per_type(qtype, model_cls):
    bank = load_exam_bank(FIXTURE_PATH)
    q = next(qq for qq in bank.questions if qq.type == qtype)
    assert isinstance(q.correct_answer_model, model_cls)


def test_choice_rationale_optional():
    bank = load_exam_bank(FIXTURE_PATH)
    q = next(qq for qq in bank.questions if qq.type == QuestionType.SINGLE_CHOICE)
    assert q.choices
    # Rationale remains schema-optional; UI does not require it.
    assert all(c.rationale is None or isinstance(c.rationale, str) for c in q.choices)


def test_invalid_yaml_raises():
    with pytest.raises(BankLoaderError):
        load_exam_bank("title: x\nquestions: []\n")


def _minimal_question(**overrides):
    base = {
        "id": "q1",
        "type": "single_choice",
        "topic_code": "1.1",
        "stem": "Stem?",
        "choices": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        "correct": {"answer": "a"},
    }
    base.update(overrides)
    return base


def test_legacy_bank_infers_cert_from_well_known_code():
    raw = {
        "title": "Legacy CCNA",
        "code": "200-301",
        "version": "v1.1",
        "topics": [{"code": "1.0", "name": "Fundamentals", "weight": 0.2}],
        "questions": [_minimal_question()],  # no cert_tags
    }
    bank = ExamBank.model_validate(raw)
    assert bank.questions[0].cert_tags == ["ccna"]


def test_legacy_bank_uses_bank_level_cert_metadata():
    raw = {
        "title": "Community pool",
        "code": "community-custom",
        "cert": "ccnp",
        "topics": [{"code": "1.0", "name": "Arch", "weight": 0.15}],
        "questions": [_minimal_question()],
    }
    bank = ExamBank.model_validate(raw)
    assert bank.questions[0].cert_tags == ["ccnp"]
    assert bank.cert_tags == ["ccnp"]


def test_legacy_bank_unknown_cert_fails():
    raw = {
        "title": "Ambiguous",
        "code": "999-999",
        "topics": [{"code": "1.0", "name": "X", "weight": 0.2}],
        "questions": [_minimal_question()],
    }
    with pytest.raises(ValidationError, match="cannot be inferred"):
        ExamBank.model_validate(raw)


def test_unknown_bank_level_cert_tag_fails():
    raw = {
        "title": "Bad cert",
        "code": "custom",
        "cert_tags": ["ccie"],
        "topics": [{"code": "1.0", "name": "X", "weight": 0.2}],
        "questions": [_minimal_question(cert_tags=["ccna"])],
    }
    with pytest.raises(ValidationError, match="Unknown certification"):
        ExamBank.model_validate(raw)


def test_malformed_bank_diagnostics(tmp_path):
    good = {
        "title": "Good",
        "code": "200-301",
        "topics": [{"code": "1.0", "name": "F", "weight": 0.2}],
        "questions": [_minimal_question(cert_tags=["ccna"])],
    }
    (tmp_path / "good.yaml").write_text(yaml.dump(good), encoding="utf-8")
    (tmp_path / "bad.yaml").write_text("title: broken\nquestions: []\n", encoding="utf-8")

    result = load_banks_detailed(tmp_path, best_effort=True)
    assert len(result.banks) == 1
    assert len(result.rejected) == 1
    assert "bad.yaml" in result.rejected[0].path
    assert result.rejected[0].reason


def test_duplicate_question_ids_rejected():
    raw = {
        "title": "Dupes",
        "code": "200-301",
        "topics": [{"code": "1.0", "name": "F", "weight": 0.2}],
        "questions": [
            _minimal_question(id="same", cert_tags=["ccna"]),
            _minimal_question(id="same", cert_tags=["ccna"], stem="Other?"),
        ],
    }
    with pytest.raises(ValidationError, match="Duplicate question ids"):
        ExamBank.model_validate(raw)


def test_topic_validation_rejects_undeclared_objective():
    raw = {
        "title": "Bad topic",
        "code": "200-301",
        "topics": [{"code": "2.0", "name": "Access", "weight": 0.2}],
        "questions": [_minimal_question(topic_code="1.1", cert_tags=["ccna"])],
    }
    with pytest.raises(ValidationError, match="not covered by bank topics"):
        ExamBank.model_validate(raw)


def test_topic_validation_allows_child_under_domain():
    raw = {
        "title": "Domain topics",
        "code": "200-301",
        "topics": [{"code": "1.0", "name": "Fundamentals", "weight": 0.2}],
        "questions": [_minimal_question(topic_code="1.1", cert_tags=["ccna"])],
    }
    bank = ExamBank.model_validate(raw)
    assert bank.questions[0].topic_code == "1.1"
