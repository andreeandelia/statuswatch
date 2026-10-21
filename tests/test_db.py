from app.checker import CheckResult
from app.db import Database


def test_save_and_read_latest():
    db = Database(":memory:")
    db.save_check("api", CheckResult(True, 10.5, "HTTP 200"), ts=100.0)
    latest = db.latest_per_service()
    assert len(latest) == 1
    row = latest[0]
    assert row["service"] == "api"
    assert row["ok"] is True
    assert row["latency_ms"] == 10.5


def test_latest_returns_newest_per_service():
    db = Database(":memory:")
    db.save_check("api", CheckResult(True, 10, "HTTP 200"), ts=100)
    db.save_check("api", CheckResult(False, None, "timeout"), ts=200)
    db.save_check("web", CheckResult(True, 5, "HTTP 200"), ts=150)
    latest = {r["service"]: r for r in db.latest_per_service()}
    assert latest["api"]["ok"] is False
    assert latest["web"]["ok"] is True


def test_recent_is_newest_first_and_limited():
    db = Database(":memory:")
    for i in range(5):
        db.save_check("api", CheckResult(True, 1, "HTTP 200"), ts=float(i))
    rows = db.recent("api", limit=3)
    assert [r["ts"] for r in rows] == [4.0, 3.0, 2.0]