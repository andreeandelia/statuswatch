import sqlite3
import time

from app.checker import CheckResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT NOT NULL,
    ts REAL NOT NULL,
    ok INTEGER NOT NULL,
    latency_ms REAL,
    detail TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checks_service_ts ON checks(service, ts);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT NOT NULL,
    started_at REAL NOT NULL,
    resolved_at REAL
);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service);
"""


def _to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    if "ok" in data:
        data["ok"] = bool(data["ok"])
    return data


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- checks ----------

    def save_check(self, service: str, result: CheckResult, ts: float | None = None):
        self.conn.execute(
            "INSERT INTO checks (service, ts, ok, latency_ms, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                service,
                ts if ts is not None else time.time(),
                int(result.ok),
                result.latency_ms,
                result.detail,
            ),
        )
        self.conn.commit()

    def latest_per_service(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT c.* FROM checks c "
            "JOIN (SELECT service, MAX(id) AS mid FROM checks GROUP BY service) m "
            "ON c.id = m.mid ORDER BY c.service"
        ).fetchall()
        return [_to_dict(r) for r in rows]

    def recent(self, service: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM checks WHERE service = ? ORDER BY id DESC LIMIT ?",
            (service, limit),
        ).fetchall()
        return [_to_dict(r) for r in rows]

    def uptime(
        self, service: str, window_seconds: float, now: float | None = None
    ) -> float | None:
        """Procentul de verificări reușite în fereastra dată. None dacă nu sunt date."""
        now = now if now is not None else time.time()
        row = self.conn.execute(
            "SELECT COUNT(*) AS total, SUM(ok) AS good FROM checks "
            "WHERE service = ? AND ts >= ?",
            (service, now - window_seconds),
        ).fetchone()
        if not row["total"]:
            return None
        return round(100 * row["good"] / row["total"], 2)

    # ---------- incidents ----------

    def open_incident(self, service: str, started_at: float) -> None:
        self.conn.execute(
            "INSERT INTO incidents (service, started_at) VALUES (?, ?)",
            (service, started_at),
        )
        self.conn.commit()

    def get_open_incident(self, service: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM incidents WHERE service = ? AND resolved_at IS NULL "
            "ORDER BY id DESC LIMIT 1",
            (service,),
        ).fetchone()
        return _to_dict(row) if row else None

    def last_incident(self, service: str) -> dict | None:
        row = self.conn.execute(
        "SELECT * FROM incidents WHERE service = ? ORDER BY id DESC LIMIT 1",
        (service,),
        ).fetchone()
        return _to_dict(row) if row else None

    def close_incident(self, incident_id: int, resolved_at: float) -> None:
        self.conn.execute(
            "UPDATE incidents SET resolved_at = ? WHERE id = ?",
            (resolved_at, incident_id),
        )
        self.conn.commit()

    def list_incidents(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_to_dict(r) for r in rows]

    def close(self):
        self.conn.close()