"""Tests for the ExSim FastAPI router.

Each test starts a new session via the API. The router's module-level state
holds active sessions; we reset it between tests to avoid bleed-over.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openboson.server import app


@pytest.fixture(autouse=True)
def _reset_router_state():
    """Clear the router's in-memory session/bank state between tests."""
    from openboson.exsim import router

    router._SESSIONS.clear()
    router._BANKS.clear()
    yield
    router._SESSIONS.clear()
    router._BANKS.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _create_session(client: TestClient, mode: str = "timed") -> dict:
    resp = client.post(
        "/api/v1/exams/200-301/sessions", json={"mode": mode}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _correct_answer_for(question: dict) -> dict | list | None:
    """Construct a correct answer payload matching the question type."""
    qid = question["id"]
    # We re-fetch the question from the bank to grab the correct answer.
    from openboson.exsim import router

    bank = router._BANKS.get("200-301")
    assert bank is not None
    q = next(qq for qq in bank.questions if qq.id == qid)
    correct = q.correct_answer_model
    if q.type.value == "single_choice":
        return {"answer": correct.answer}
    if q.type.value == "multiple_choice":
        return {"answers": list(correct.answers)}
    if q.type.value == "ordered_list":
        return {"order": list(correct.order)}
    if q.type.value == "drag_match":
        return {"pairs": [{"left": p.left, "right": p.right} for p in correct.pairs]}
    if q.type.value == "sim":
        return {"config": "\n".join(correct.expected_commands or [])}
    return None


def test_list_exams_loads_demo_bank(client):
    resp = client.get("/api/v1/exams")
    assert resp.status_code == 200
    body = resp.json()
    codes = {e["id"] for e in body}
    assert "200-301" in codes
    for e in body:
        if e["id"] == "200-301":
            assert e["question_count"] == 6
            assert e["pass_score"] == pytest.approx(0.825)


def test_create_session_returns_first_question(client):
    body = _create_session(client)
    assert body["mode"] == "timed"
    assert body["total_questions"] == 6
    q = body["question"]
    assert "correct" not in q  # correctness must never leak
    assert "id" in q
    assert q["type"] in {"single_choice", "multiple_choice", "ordered_list", "drag_match", "sim"}


def test_create_session_unknown_exam_404(client):
    resp = client.post("/api/v1/exams/nope/sessions", json={"mode": "timed"})
    assert resp.status_code == 404


def test_get_question_by_index(client):
    body = _create_session(client)
    session_id = body["session_id"]
    resp = client.get(f"/api/v1/sessions/{session_id}/questions/2")
    assert resp.status_code == 200
    q = resp.json()
    assert "correct" not in q
    assert q["id"] == body["question"]["id"] or "id" in q


def test_submit_answer_accepted_timed(client):
    body = _create_session(client, mode="timed")
    session_id = body["session_id"]
    q = body["question"]
    payload = _correct_answer_for(q) or {"answer": "x"}
    resp = client.post(
        f"/api/v1/sessions/{session_id}/answers",
        json={"question_id": q["id"], "answer": payload},
    )
    assert resp.status_code == 200
    body2 = resp.json()
    assert body2["accepted"] is True
    # Timed mode: is_correct is NOT returned (deferred until finish).
    assert "is_correct" not in body2


def test_submit_answer_study_mode_grades_immediately(client):
    body = _create_session(client, mode="study")
    session_id = body["session_id"]
    q = body["question"]
    payload = _correct_answer_for(q) or {"answer": "x"}
    resp = client.post(
        f"/api/v1/sessions/{session_id}/answers",
        json={"question_id": q["id"], "answer": payload},
    )
    body2 = resp.json()
    assert body2.get("is_correct") is True


def test_toggle_bookmark(client):
    body = _create_session(client)
    sid = body["session_id"]
    qid = body["question"]["id"]
    resp = client.post(
        f"/api/v1/sessions/{sid}/bookmark", json={"question_id": qid}
    )
    assert resp.status_code == 200
    assert resp.json()["bookmarked"] is True
    # Toggle off
    resp2 = client.post(
        f"/api/v1/sessions/{sid}/bookmark", json={"question_id": qid}
    )
    assert resp2.json()["bookmarked"] is False


def test_finish_session_returns_result(client):
    body = _create_session(client)
    sid = body["session_id"]
    # Answer the first question correctly.
    q = body["question"]
    payload = _correct_answer_for(q)
    if payload is None:
        payload = {"answer": "x"}
    client.post(
        f"/api/v1/sessions/{sid}/answers",
        json={"question_id": q["id"], "answer": payload},
    )
    resp = client.post(f"/api/v1/sessions/{sid}/finish")
    assert resp.status_code == 200
    result = resp.json()
    assert result["session_id"] == sid
    assert result["exam_code"] == "200-301"
    assert result["total_questions"] == 6
    assert result["correct_count"] == 1
    assert "domain_breakdown" in result


def test_review_session_includes_explanations_and_correct(client):
    body = _create_session(client)
    sid = body["session_id"]
    q = body["question"]
    client.post(
        f"/api/v1/sessions/{sid}/answers",
        json={"question_id": q["id"], "answer": _correct_answer_for(q) or {"answer": "x"}},
    )
    client.post(f"/api/v1/sessions/{sid}/finish")
    resp = client.get(f"/api/v1/sessions/{sid}/review")
    assert resp.status_code == 200
    review = resp.json()
    assert len(review["items"]) == 6
    for item in review["items"]:
        assert "correct" in item
        assert "explanation" in item


def test_review_session_not_finished_returns_400(client):
    body = _create_session(client)
    sid = body["session_id"]
    resp = client.get(f"/api/v1/sessions/{sid}/review")
    assert resp.status_code == 400


def test_unknown_session_404(client):
    resp = client.get("/api/v1/sessions/nonexistent/questions/0")
    assert resp.status_code == 404


def test_question_payload_does_not_leak_correct_answer(client):
    body = _create_session(client)
    q = body["question"]
    forbidden = {"correct", "correct_answer", "correct_answer_json", "explanation"}
    assert not (set(q) & forbidden), f"Question response leaked: {set(q) & forbidden}"
