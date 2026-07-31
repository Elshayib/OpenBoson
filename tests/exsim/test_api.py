"""Tests for the ExSim FastAPI router."""

from __future__ import annotations

from collections import Counter

import pytest
from fastapi.testclient import TestClient

from openboson.exsim.blueprint import allocate_counts, get_blueprint
from openboson.server import app

BLUEPRINT_ID = "ccna-200-301"
EXAM_CODE = "200-301"


@pytest.fixture(autouse=True)
def _reset_router_state():
    from openboson.exsim import router

    router._SESSIONS.clear()
    router._BANKS.clear()
    router._POOL = None
    yield
    router._SESSIONS.clear()
    router._BANKS.clear()
    router._POOL = None


@pytest.fixture
def client(isolated_home) -> TestClient:
    return TestClient(app)


def _create_session(client: TestClient, exam_id: str = BLUEPRINT_ID, mode: str = "exam") -> dict:
    resp = client.post(f"/api/v1/exams/{exam_id}/sessions", json={"mode": mode})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _correct_answer_for(question: dict) -> dict | list | None:
    from openboson.exsim import router

    session = next(iter(router._SESSIONS.values()))
    q = next(qq for qq in session.questions if qq.id == question["id"])
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


def test_list_exams_returns_blueprints_not_raw_pools(client):
    resp = client.get("/api/v1/exams")
    assert resp.status_code == 200
    body = resp.json()
    ids = {e["id"] for e in body}
    assert "ccna-200-301" in ids
    assert "encor-350-401" in ids
    assert "pool-ccna" not in ids
    assert "pool-encor" not in ids
    assert "pool" not in ids
    enabled = {e["id"] for e in body if e.get("enabled")}
    assert "ccna-200-301" in enabled
    for item in body:
        if item["id"] in ("ccna-200-301", "encor-350-401"):
            assert item["question_count"] == 100


def test_create_session_uses_exact_blueprint_count(client):
    body = _create_session(client)
    assert body["mode"] == "exam"
    assert body["total_questions"] == 100
    assert body["blueprint_id"] == BLUEPRINT_ID
    assert body["exam_code"] == EXAM_CODE
    q = body["question"]
    assert "correct" not in q
    assert "id" in q


def test_create_session_domain_quotas(client):
    body = _create_session(client)
    from openboson.exsim import router

    session = router._SESSIONS[body["session_id"]]
    bp = get_blueprint(BLUEPRINT_ID)
    expected = allocate_counts(bp.question_count, bp.domain_weights)
    actual = Counter(q.topic_code.split(".", 1)[0] for q in session.questions)
    assert dict(actual) == expected
    assert all(q.matches_cert("ccna") for q in session.questions)


def test_create_session_code_alias(client):
    body = _create_session(client, exam_id="200-301")
    assert body["blueprint_id"] == "ccna-200-301"
    assert body["total_questions"] == 100


def test_create_session_rejects_raw_pool(client):
    resp = client.post("/api/v1/exams/pool-ccna/sessions", json={"mode": "exam"})
    assert resp.status_code == 404


def test_create_session_unknown_exam_404(client):
    resp = client.post("/api/v1/exams/nope/sessions", json={"mode": "exam"})
    assert resp.status_code == 404


def test_get_question_by_index(client):
    body = _create_session(client)
    session_id = body["session_id"]
    resp = client.get(f"/api/v1/sessions/{session_id}/questions/2")
    assert resp.status_code == 200
    q = resp.json()
    assert "correct" not in q
    assert "id" in q


def test_submit_answer_accepted_exam(client):
    body = _create_session(client, mode="exam")
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
    assert "is_correct" not in body2


def test_submit_answer_practice_mode_grades_immediately(client):
    body = _create_session(client, mode="practice")
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
    resp = client.post(f"/api/v1/sessions/{sid}/bookmark", json={"question_id": qid})
    assert resp.status_code == 200
    assert resp.json()["bookmarked"] is True
    resp2 = client.post(f"/api/v1/sessions/{sid}/bookmark", json={"question_id": qid})
    assert resp2.json()["bookmarked"] is False


def test_finish_session_returns_result(client):
    body = _create_session(client)
    sid = body["session_id"]
    q = body["question"]
    payload = _correct_answer_for(q) or {"answer": "x"}
    client.post(
        f"/api/v1/sessions/{sid}/answers",
        json={"question_id": q["id"], "answer": payload},
    )
    resp = client.post(f"/api/v1/sessions/{sid}/finish")
    assert resp.status_code == 200
    result = resp.json()
    assert result["session_id"] == sid
    assert result["exam_code"] == EXAM_CODE
    assert result["total_questions"] == 100
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
    assert len(review["items"]) == 100
    for item in review["items"][:5]:
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


def test_drag_match_does_not_leak_canonical_pairs(client):
    body = _create_session(client)
    sid = body["session_id"]
    from openboson.exsim import router

    session = router._SESSIONS[sid]
    drag_idxs = [i for i, q in enumerate(session.questions) if q.type.value == "drag_match"]
    if not drag_idxs:
        pytest.skip("no drag_match questions in sampled exam")
    resp = client.get(f"/api/v1/sessions/{sid}/questions/{drag_idxs[0]}")
    assert resp.status_code == 200
    q = resp.json()
    assert "drag_pairs" not in q
    assert "correct" not in q
    assert "left_items" in q and "right_items" in q
    left_ids = {item["id"] for item in q["left_items"]}
    right_ids = {item["id"] for item in q["right_items"]}
    assert left_ids.isdisjoint(right_ids)
    # No pairing field that reveals which left maps to which right.
    for item in q["left_items"] + q["right_items"]:
        assert set(item.keys()) <= {"id", "text"}


def test_choice_presentation_stable_across_fetches(client):
    body = _create_session(client)
    sid = body["session_id"]
    from openboson.exsim import router

    session = router._SESSIONS[sid]
    sc_idx = next(i for i, q in enumerate(session.questions) if q.type.value == "single_choice")
    r1 = client.get(f"/api/v1/sessions/{sid}/questions/{sc_idx}").json()
    r2 = client.get(f"/api/v1/sessions/{sid}/questions/{sc_idx}").json()
    assert [c["id"] for c in r1["choices"]] == [c["id"] for c in r2["choices"]]


def test_encor_session_cert_isolation(client):
    body = _create_session(client, exam_id="encor-350-401")
    assert body["total_questions"] == 100
    from openboson.exsim import router

    session = router._SESSIONS[body["session_id"]]
    assert all(q.matches_cert("ccnp") for q in session.questions)
    bp = get_blueprint("encor-350-401")
    expected = allocate_counts(bp.question_count, bp.domain_weights)
    actual = Counter(q.topic_code.split(".", 1)[0] for q in session.questions)
    assert dict(actual) == expected


def test_pause_resume_list_and_mark(client):
    body = _create_session(client)
    sid = body["session_id"]
    qid = body["question"]["id"]

    mark = client.post(f"/api/v1/sessions/{sid}/mark", json={"question_id": qid})
    assert mark.status_code == 200
    assert mark.json()["marked_for_review"] is True

    paused = client.post(
        f"/api/v1/sessions/{sid}/pause",
        json={"remaining_seconds": 3210},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert paused.json()["remaining_seconds"] == 3210

    listed = client.get("/api/v1/sessions")
    assert listed.status_code == 200
    assert any(item["session_id"] == sid for item in listed.json())

    # Drop memory — load must come from SQLite.
    from openboson.exsim import router

    router._SESSIONS.clear()
    resumed = client.post(f"/api/v1/sessions/{sid}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "in_progress"
    assert resumed.json()["remaining_seconds"] == 3210

    meta = client.get(f"/api/v1/sessions/{sid}")
    assert meta.status_code == 200
    assert qid in meta.json()["marked_for_review"]
