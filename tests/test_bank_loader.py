"""Tests for question-bank schema and loader."""

from pathlib import Path

import pytest

from openboson.bank_loader import BankLoaderError, load_exam_bank, load_question_pool
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


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_bank.yaml"
BANKS_DIR = Path(__file__).resolve().parents[1] / "data" / "demo_banks"


def test_fixture_bank_loads_from_file():
    bank = load_exam_bank(FIXTURE_PATH)
    assert isinstance(bank, ExamBank)
    assert bank.code == "fixture-200-301"
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


def test_choice_rationale_present():
    bank = load_exam_bank(FIXTURE_PATH)
    q = next(qq for qq in bank.questions if qq.type == QuestionType.SINGLE_CHOICE)
    assert any(c.rationale for c in (q.choices or []))


def test_invalid_yaml_raises():
    with pytest.raises(BankLoaderError):
        load_exam_bank("title: x\nquestions: []\n")
