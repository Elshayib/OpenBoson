"""Tests for the NetSim session engine + FastAPI router."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openboson.netsim.lab_loader import load_lab
from openboson.netsim.router import _LABS, _SESSIONS
from openboson.netsim.session import LabSession, score_lab
from openboson.server import app

LAB_ID = "ccna_branch_office_access"
LAB_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_labs" / f"{LAB_ID}.yaml"


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
    s.submit_task(lab.tasks[0].expected_config)
    s.goto(1)
    s.submit_task("hostname SW1\n")
    result = score_lab(s)
    assert result.passed_tasks == 1
    assert result.total_tasks == len(lab.tasks)
    assert result.score == pytest.approx(1 / len(lab.tasks))


def test_list_labs(client):
    resp = client.get("/api/v1/labs")
    assert resp.status_code == 200
    body = resp.json()
    ids = {item["id"] for item in body}
    assert LAB_ID in ids
    sample = next(item for item in body if item["id"] == LAB_ID)
    assert "objectives" in sample
    assert "cert_tags" in sample


def test_list_labs_filters(client):
    all_labs = client.get("/api/v1/labs").json()
    assert all_labs
    topic = all_labs[0]["topic_code"]
    filtered = client.get("/api/v1/labs", params={"topic_code": topic}).json()
    assert filtered
    assert all(item["topic_code"] == topic for item in filtered)
    empty = client.get("/api/v1/labs", params={"q": "zzzz-no-lab-zzzz"}).json()
    assert empty == []


def test_create_lab_session_returns_topology_and_task(client):
    resp = client.post(f"/api/v1/labs/{LAB_ID}/sessions", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["lab_id"] == LAB_ID
    assert body["task_count"] == 4
    assert "devices" in body["topology"]
    assert "instructions" in body["task"]


def test_create_unknown_lab_404(client):
    resp = client.post("/api/v1/labs/nope/sessions", json={})
    assert resp.status_code == 404


def test_submit_config_grades(client):
    sess = client.post(f"/api/v1/labs/{LAB_ID}/sessions", json={}).json()
    sid = sess["session_id"]
    lab = _LABS[LAB_ID]
    t1 = next(t for t in lab.tasks if t.id == "t1")
    resp = client.post(f"/api/v1/lab-sessions/{sid}/submit", json={"config": t1.expected_config})
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "t1"
    assert body["is_correct"] is True


def test_finish_lab_returns_result(client):
    sess = client.post(f"/api/v1/labs/{LAB_ID}/sessions", json={}).json()
    sid = sess["session_id"]
    lab = _LABS[LAB_ID]
    for t in lab.tasks:
        client.post(f"/api/v1/lab-sessions/{sid}/submit", json={"config": t.expected_config})
    resp = client.post(f"/api/v1/lab-sessions/{sid}/finish")
    assert resp.status_code == 200
    result = resp.json()
    assert result["passed_tasks"] == len(lab.tasks)
    assert result["score"] == pytest.approx(1.0)


def test_unknown_session_404(client):
    resp = client.post("/api/v1/lab-sessions/xyz/submit", json={"config": "x"})
    assert resp.status_code == 404


def test_check_current_task_from_live_cli(lab):
    s = LabSession.create(lab)
    r1 = s.world.shell("R1")
    for line in (
        "en",
        "conf t",
        "int g0/0",
        "ip address 10.10.10.1 255.255.255.0",
        "no shutdown",
        "end",
    ):
        r1.feed(line)
    g = s.check_current_task()
    assert g.is_correct is True
    assert "Objective met" in g.feedback
