"""Tests for SQLite active-exam session store."""

from __future__ import annotations

from pathlib import Path

import pytest

from openboson.bank_loader import load_exam_bank
from openboson.exsim import session_store
from openboson.exsim.scoring import score_exam
from openboson.exsim.session import ExamMode, ExamSession, SessionStatus

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_bank.yaml"

pytestmark = pytest.mark.usefixtures("isolated_home")


@pytest.fixture
def bank():
    return load_exam_bank(FIXTURE)


def test_upsert_and_load_survives_engine_reset(bank, monkeypatch):
    s = ExamSession.create(bank, mode=ExamMode.EXAM, shuffle=False, seed=7)
    q = s.questions[0]
    s.submit_answer(q.id, {"answer": "x"}, grade_now=False)
    s.toggle_bookmark(q.id)
    s.goto(2)
    s.pause(s.remaining_seconds - 12 if s.remaining_seconds else 100)
    session_store.upsert_active_session(s)

    # Simulate process restart: drop in-process engine handle.
    monkeypatch.setattr(session_store, "_engine", None)
    info = session_store.get_resumable_info()
    assert info is not None
    assert info.engine_session_id == s.session_id
    assert info.status == SessionStatus.PAUSED.value
    assert info.current_index == 2

    by_id = {q.id: q for q in bank.questions}
    restored = session_store.load_active_session(by_id)
    assert restored is not None
    assert restored.current_index == 2
    assert q.id in restored.bookmarked
    assert restored.answers[q.id].answer == {"answer": "x"}
    assert restored.remaining_seconds == s.remaining_seconds
    assert restored.is_paused()


def test_finalize_marks_finished_and_clears_resumable(bank):
    s = ExamSession.create(bank, mode=ExamMode.EXAM, shuffle=False)
    session_store.upsert_active_session(s)
    s.finish()
    result = score_exam(s)
    session_store.finalize_session(s, result)
    assert session_store.get_resumable_info() is None


def test_abandon_active_sessions(bank):
    s = ExamSession.create(bank, shuffle=False)
    session_store.upsert_active_session(s)
    assert session_store.abandon_active_sessions() == 1
    assert session_store.get_resumable_info() is None
