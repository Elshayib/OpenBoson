"""Tests for question-bank schema and loader."""

from pathlib import Path

import pytest

from openboson.bank_loader import BankLoaderError, load_exam_bank
from openboson.bank_schema import (
    ExamBank,
    Question,
    QuestionType,
    SingleChoiceAnswer,
    MultipleChoiceAnswer,
    DragMatchAnswer,
    OrderedListAnswer,
    SimAnswer,
)


DEMO_BANK_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_banks" / "ccna_200_301_v1.1_demo.yaml"


def test_demo_bank_loads_from_file():
    bank = load_exam_bank(DEMO_BANK_PATH)
    assert isinstance(bank, ExamBank)
    assert bank.code == "200-301"
    assert bank.version == "v1.1"
    assert len(bank.questions) == 6


def test_demo_bank_covers_all_six_domains():
    bank = load_exam_bank(DEMO_BANK_PATH)
    prefixes = {q.topic_code.split(".")[0] + ".0" for q in bank.questions}
    assert prefixes == {"1.0", "2.0", "3.0", "4.0", "5.0", "6.0"}


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
def test_question_correct_answer_model(qtype, model_cls):
    bank = load_exam_bank(DEMO_BANK_PATH)
    qs = [q for q in bank.questions if q.type == qtype]
    assert qs, f"no question of type {qtype} in demo bank"
    for q in qs:
        assert isinstance(q.correct_answer_model, model_cls)


def test_invalid_yaml_raises():
    bad_yaml = """
    title: x
    code: "x"
    topics: []
    questions: []
    """
    with pytest.raises(BankLoaderError):
        load_exam_bank(bad_yaml)


def test_missing_file_raises():
    with pytest.raises(BankLoaderError):
        load_exam_bank("/no/such/path/foo.yaml")


def test_topic_codes_property():
    bank = load_exam_bank(DEMO_BANK_PATH)
    codes = bank.topic_codes
    assert "1.0" in codes
    assert "6.1" in codes


def test_domain_weight_sums_correctly():
    bank = load_exam_bank(DEMO_BANK_PATH)
    # "1." should sum all topics starting with 1. — 1.0 (0.20) + 1.1 (0.05) = 0.25
    assert bank.domain_weight("1.") == pytest.approx(0.25)


def test_single_choice_question_validates():
    q = bank_question_by_id(load_exam_bank(DEMO_BANK_PATH), "q1")
    assert q.type == QuestionType.SINGLE_CHOICE
    assert q.correct_answer_model.answer == "a"


def bank_question_by_id(bank: ExamBank, qid: str) -> Question:
    for q in bank.questions:
        if q.id == qid:
            return q
    raise KeyError(qid)
