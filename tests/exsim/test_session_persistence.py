"""Tests for ExamSession snapshot / pause / resume."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.exsim.session import ExamMode, ExamSession, SessionStatus

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"


@pytest.fixture
def bank():
    return load_exam_bank(FIXTURE)


def test_snapshot_round_trip_preserves_answers_and_marks(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM, shuffle=False, seed=1)
    q0 = s.questions[0]
    s.submit_answer(q0.id, {"answer": "a"}, grade_now=False)
    s.toggle_bookmark(q0.id)
    s.toggle_mark_for_review(q0.id)
    s.goto(1)
    snap = s.to_snapshot()
    by_id = {q.id: q for q in bank.questions}
    restored = ExamSession.from_snapshot(snap, by_id)
    assert restored.session_id == s.session_id
    assert restored.current_index == 1
    assert q0.id in restored.bookmarked
    assert q0.id in restored.marked_for_review
    assert restored.answers[q0.id].answer == {"answer": "a"}
    assert [q.id for q in restored.questions] == [q.id for q in s.questions]
    assert restored.presentation[q0.id].to_dict() == s.presentation[q0.id].to_dict()


def test_pause_freezes_remaining_across_wall_clock(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM, shuffle=False)
    assert s.remaining_seconds is not None
    before = s.remaining_seconds
    s.pause(before - 30)
    assert s.status == SessionStatus.PAUSED
    assert s.remaining_seconds == before - 30
    time.sleep(0.05)
    assert s.remaining_seconds == before - 30
    s.resume()
    assert s.status == SessionStatus.IN_PROGRESS
    assert s.remaining_seconds == before - 30
    assert s.paused_at is None


def test_finish_sets_finished_status(bank):
    s = ExamSession.create(bank, shuffle=False)
    s.finish()
    assert s.is_finished()
    assert s.status == SessionStatus.FINISHED
    with pytest.raises(RuntimeError):
        s.pause(10)
