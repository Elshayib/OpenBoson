"""Tests for the NetSim session engine + FastAPI router."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.router import _LABS, _SESSIONS
from openboson.netsim.session import LabSession, score_lab
from openboson.server import app


LAB_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / "ccna_basic_rtr_sw.yaml"


@pytest.fixture(autouse=True)
def _reset():
    _LABS.clear()
    _SESSIONS.clear()
    yield
    _LABS.clear()
    _SESSIONS.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def lab():
    return load_lab(LAB_PATH)


def test_session_create_and_grade(lab):
    s = LabSession.create(lab)
    assert s.current_task.id == lab.tasks[0].id
    g = s.submit_task(lab.tasks[0].expected_config)
    assert g.is_correct is True
    assert s.grades[lab.tasks[0].id].is_correct is True


def test_session_navigation(lab):
    s = LabSession.create(lab)
    t2 = s.next_task()
    assert t2.id == lab.tasks[1].id
    t1 = s.previous_task()
    assert t1.id == lab.tasks[0].id


def test_score_lab_all_correct(lab):
    s = LabSession.create(lab)
    for t in lab.tasks:
        s.submit_task(t.expected_config)
        s.next_task()
    result = score_lab(s)
    assert result.passed_tasks == result.total_tasks
    assert result.score == 1.0


def test_score_lab_partial(lab):
    s = LabSession.create(lab)
    # Only first task correct.
    s.submit_task(lab.tasks[0].expected_config)
    s.goto(1)
    s.submit_task("hostname SW1\n")  # missing vlan + trunk
    result = score_lab(s)
    assert result.passed_tasks == 1
    assert result.total_tasks == 2
    assert result.score == pytest.approx(0.5)


# ----- Router -----
def test_list_labs(client):
    resp = client.get("/api/v1/labs")
    assert resp.status_code == 200
    labs = resp.json()
    ids = {l["id"] for l in labs}
    assert "ccna_basic_rtr_sw" in ids


def test_create_lab_session_returns_topology_and_task(client):
    resp = client.post("/api/v1/labs/ccna_basic_rtr_sw/sessions", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["lab_id"] == "ccna_basic_rtr_sw"
    assert body["task_count"] == 2
    assert "devices" in body["topology"]
    assert "instructions" in body["task"]


def test_create_unknown_lab_404(client):
    resp = client.post("/api/v1/labs/nope/sessions", json={})
    assert resp.status_code == 404


def test_submit_config_grades(client):
    sess = client.post("/api/v1/labs/ccna_basic_rtr_sw/sessions", json={}).json()
    sid = sess["session_id"]
    # First task is t1 (hostname R1 etc.)
    from openboson.netsim.router import _LABS

    lab = _LABS["ccna_basic_rtr_sw"]
    t1 = next(t for t in lab.tasks if t.id == "t1")
    resp = client.post(f"/api/v1/lab-sessions/{sid}/submit", json={"config": t1.expected_config})
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "t1"
    assert body["is_correct"] is True


def test_finish_lab_returns_result(client):
    sess = client.post("/api/v1/labs/ccna_basic_rtr_sw/sessions", json={}).json()
    sid = sess["session_id"]
    from openboson.netsim.router import _LABS

    lab = _LABS["ccna_basic_rtr_sw"]
    for t in lab.tasks:
        client.post(f"/api/v1/lab-sessions/{sid}/submit", json={"config": t.expected_config})
    resp = client.post(f"/api/v1/lab-sessions/{sid}/finish")
    assert resp.status_code == 200
    result = resp.json()
    assert result["passed_tasks"] == 2
    assert result["score"] == pytest.approx(1.0)


def test_unknown_session_404(client):
    resp = client.post("/api/v1/lab-sessions/xyz/submit", json={"config": "x"})
    assert resp.status_code == 404
