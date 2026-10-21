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
"""


def _to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["ok"] = bool(data["ok"])
    return data


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

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

    def close(self):
        self.conn.close()