from app.checker import CheckResult
from app.db import Database
from app.incidents import update_incidents


def add(db: Database, ok: bool, ts: float) -> None:
    db.save_check("api", CheckResult(ok, 1.0 if ok else None, "x"), ts=ts)


# ---------- incidente ----------

def test_incident_opens_after_threshold_with_first_failure_time():
    db = Database(":memory:")
    add(db, False, 100)
    assert update_incidents(db, "api", 3) is None
    add(db, False, 130)
    assert update_incidents(db, "api", 3) is None
    add(db, False, 160)
    assert update_incidents(db, "api", 3) == "opened"

    incident = db.get_open_incident("api")
    assert incident["started_at"] == 100.0
    assert incident["resolved_at"] is None


def test_no_duplicate_incident_while_still_down():
    db = Database(":memory:")
    for ts in (100, 130, 160):
        add(db, False, ts)
        update_incidents(db, "api", 3)
    add(db, False, 190)
    assert update_incidents(db, "api", 3) is None
    assert len(db.list_incidents()) == 1


def test_incident_resolves_on_success():
    db = Database(":memory:")
    for ts in (100, 130, 160):
        add(db, False, ts)
        update_incidents(db, "api", 3)
    add(db, True, 220)
    assert update_incidents(db, "api", 3) == "resolved"

    assert db.get_open_incident("api") is None
    assert db.list_incidents()[0]["resolved_at"] == 220.0


def test_success_resets_failure_streak():
    db = Database(":memory:")
    for ok, ts in [(False, 100), (False, 130), (True, 160), (False, 190)]:
        add(db, ok, ts)
        assert update_incidents(db, "api", 3) is None
    assert db.list_incidents() == []


# ---------- uptime ----------

def test_uptime_ratio():
    db = Database(":memory:")
    for ts, ok in [(100, True), (110, True), (120, True), (130, False)]:
        add(db, ok, ts)
    assert db.uptime("api", 1000, now=200) == 75.0


def test_uptime_window_excludes_old_checks():
    db = Database(":memory:")
    add(db, False, 0)
    add(db, True, 900)
    assert db.uptime("api", 200, now=1000) == 100.0


def test_uptime_is_none_without_data():
    db = Database(":memory:")
    assert db.uptime("api", 1000, now=200) is None