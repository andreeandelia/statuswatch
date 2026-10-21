from app.config import Service
from app.db import Database
from app.scheduler import run_cycle


async def test_run_cycle_saves_one_row_per_service():
    db = Database(":memory:")
    services = [
        Service(name="local dns", type="dns", target="localhost"),
        Service(name="bad dns", type="dns", target="does-not-exist.invalid"),
    ]
    await run_cycle(services, db)
    latest = {r["service"]: r for r in db.latest_per_service()}
    assert latest["local dns"]["ok"] is True
    assert latest["bad dns"]["ok"] is False


async def test_unknown_type_is_reported_as_failure():
    db = Database(":memory:")
    await run_cycle([Service(name="weird", type="ftp", target="x")], db)
    row = db.latest_per_service()[0]
    assert row["ok"] is False
    assert "unknown type" in row["detail"]

async def test_cycle_opens_incident_after_threshold():
    db = Database(":memory:")
    svc = [Service(name="bad dns", type="dns", target="does-not-exist.invalid")]
    await run_cycle(svc, db, failure_threshold=2)
    assert db.get_open_incident("bad dns") is None
    await run_cycle(svc, db, failure_threshold=2)
    assert db.get_open_incident("bad dns") is not None