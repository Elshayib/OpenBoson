"""Tests for exam score/review export (including redacted mode)."""

from __future__ import annotations

import json
from pathlib import Path

from openboson.bank_loader import load_exam_bank
from openboson.exsim.export import build_export_payload, to_csv, to_html, to_json, write_export
from openboson.exsim.scoring import score_exam
from openboson.exsim.session import ExamMode, ExamSession

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


def _finished_session():
    bank = load_exam_bank(FIXTURE)
    session = ExamSession.create(bank, mode=ExamMode.EXAM, shuffle=False)
    for q in session.questions:
        correct = q.correct_answer_model
        if q.type.value == "single_choice":
            session.submit_answer(q.id, {"answer": correct.answer}, grade_now=False)
        elif q.type.value == "multiple_choice":
            session.submit_answer(q.id, {"answers": list(correct.answers)}, grade_now=False)
        elif q.type.value == "ordered_list":
            session.submit_answer(q.id, {"order": list(correct.order)}, grade_now=False)
        elif q.type.value == "drag_match":
            session.submit_answer(
                q.id,
                {"pairs": [{"left": p.left, "right": p.right} for p in correct.pairs]},
                grade_now=False,
            )
        elif q.type.value == "sim":
            session.submit_answer(
                q.id,
                {"config": "\n".join(correct.expected_commands or [])},
                grade_now=False,
            )
    session.finish()
    return session, score_exam(session)


def test_full_export_includes_answers_and_explanations():
    session, result = _finished_session()
    payload = build_export_payload(session, result, redacted=False)
    assert payload["redacted"] is False
    assert "correct_count" in payload
    item = payload["items"][0]
    assert "correct" in item
    assert "explanation" in item
    assert "is_correct" in item
    raw = to_json(session, result, redacted=False)
    data = json.loads(raw)
    assert data["items"][0]["correct"]


def test_redacted_export_omits_keys_and_explanations():
    session, result = _finished_session()
    # Grab a distinctive explanation substring to assert absence.
    sample_expl = next(
        (q.explanation for q in session.questions if q.explanation),
        None,
    )
    payload = build_export_payload(session, result, redacted=True)
    assert payload["redacted"] is True
    assert "correct_count" not in payload
    for item in payload["items"]:
        assert "correct" not in item
        assert "explanation" not in item
        assert "is_correct" not in item
        assert "choices" not in item
        assert "stem" in item
        assert "user_answer" in item

    text = to_json(session, result, redacted=True) + to_csv(session, result, redacted=True)
    text += to_html(session, result, redacted=True)
    assert '"correct"' not in text or "correct answers" in text.lower()
    # Ensure correct answer blobs / explanations do not leak as structured fields.
    assert "is_correct" not in text
    assert "explanation" not in text.lower() or "explanations omitted" in text.lower()
    if sample_expl and len(sample_expl) > 20:
        assert sample_expl[:40] not in text


def test_write_export_json(tmp_path):
    session, result = _finished_session()
    path = write_export(tmp_path / "out.json", session, "json", result, redacted=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["redacted"] is True
    assert data["passed"] in (True, False)
