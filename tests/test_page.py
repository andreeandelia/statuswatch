from fastapi.testclient import TestClient

from app.checker import CheckResult
from app.main import app, format_duration


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("STATUSWATCH_SCHEDULER", "0")
    monkeypatch.setenv("STATUSWATCH_DB", str(tmp_path / "test.db"))
    return TestClient(app)


def test_page_waiting_when_no_data(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Waiting for first checks" in response.text


def test_page_all_operational(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        client.app.state.db.save_check("svc", CheckResult(True, 12.3, "HTTP 200"))
        response = client.get("/")
        assert response.status_code == 200
        assert "All systems operational" in response.text
        assert "svc" in response.text


def test_page_shows_incident(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        db = client.app.state.db
        db.save_check("svc", CheckResult(False, None, "timeout"))
        db.open_incident("svc", 1000.0)
        response = client.get("/")
        assert "Incident in progress" in response.text
        assert "Ongoing" in response.text


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3 * 3600 + 120) == "3h 2m"
    assert format_duration(2 * 86400 + 5 * 3600) == "2d 5h"