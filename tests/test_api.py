from fastapi.testclient import TestClient

from app.checker import CheckResult
from app.main import app


def test_status_and_history_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv("STATUSWATCH_SCHEDULER", "0")
    monkeypatch.setenv("STATUSWATCH_DB", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        client.app.state.db.save_check("svc", CheckResult(True, 12.3, "HTTP 200"))

        status = client.get("/api/status").json()
        assert status[0]["service"] == "svc"
        assert status[0]["ok"] is True

        history = client.get("/api/history", params={"service": "svc"}).json()
        assert len(history) == 1

def test_incidents_endpoint_and_status_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("STATUSWATCH_SCHEDULER", "0")
    monkeypatch.setenv("STATUSWATCH_DB", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        db = client.app.state.db
        db.save_check("svc", CheckResult(True, 1.0, "HTTP 200"))
        db.open_incident("svc", 1000.0)

        status = client.get("/api/status").json()[0]
        assert status["uptime_24h"] == 100.0
        assert status["open_incident"]["service"] == "svc"

        incidents = client.get("/api/incidents").json()
        assert len(incidents) == 1
        assert incidents[0]["resolved_at"] is None