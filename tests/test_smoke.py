"""Smoke test for the engine HTTP server."""

from fastapi.testclient import TestClient

from openboson.server import app


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_health_reports_version():
    from openboson import __version__

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.json()["version"] == __version__
