import asyncio
import os
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import load_services
from app.db import Database
from app.scheduler import run_forever

DAY = 24 * 3600

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["dt"] = lambda ts: datetime.fromtimestamp(
    ts, tz=timezone.utc
).strftime("%Y-%m-%d %H:%M UTC")


from app.notifier import WebhookNotifier
from app.utils import format_duration


def build_status(db: Database) -> list[dict]:
    result = []
    for row in db.latest_per_service():
        name = row["service"]
        row["uptime_24h"] = db.uptime(name, DAY)
        row["uptime_7d"] = db.uptime(name, 7 * DAY)
        row["open_incident"] = db.get_open_incident(name)
        result.append(row)
    return result


def build_banner(services: list[dict]) -> tuple[str, str]:
    if not services:
        return "idle", "Waiting for first checks..."
    if any(s["open_incident"] for s in services):
        return "bad", "Incident in progress"
    if any(not s["ok"] for s in services):
        return "warn", "Some checks are failing"
    return "ok", "All systems operational"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(os.getenv("STATUSWATCH_DB", "statuswatch.db"))
    app.state.db = db

    task = None
    if os.getenv("STATUSWATCH_SCHEDULER", "1") != "0":
        services = load_services(os.getenv("STATUSWATCH_SERVICES", "services.json"))
        interval = float(os.getenv("STATUSWATCH_INTERVAL", "30"))
        threshold = int(os.getenv("STATUSWATCH_FAILURE_THRESHOLD", "3"))

        webhook_url = os.getenv("STATUSWATCH_WEBHOOK_URL")
        notifier = (
            WebhookNotifier(webhook_url, os.getenv("STATUSWATCH_WEBHOOK_KIND", "discord"))
            if webhook_url
            else None
        )
        task = asyncio.create_task(
            run_forever(services, db, interval, threshold, notifier)
        )

    yield

    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    db.close()


app = FastAPI(title="StatusWatch", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def status_page(request: Request):
    db = app.state.db
    services = build_status(db)
    banner_class, banner_text = build_banner(services)

    now = time.time()
    incidents = db.list_incidents(10)
    for incident in incidents:
        end = incident["resolved_at"] or now
        incident["duration"] = format_duration(end - incident["started_at"])

    return templates.TemplateResponse(
        request,
        "status.html",
        {
            "services": services,
            "incidents": incidents,
            "banner_class": banner_class,
            "banner_text": banner_text,
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return build_status(app.state.db)


@app.get("/api/history")
def history(service: str, limit: int = 50):
    return app.state.db.recent(service, min(limit, 500))


@app.get("/api/incidents")
def incidents(limit: int = 50):
    return app.state.db.list_incidents(min(limit, 500))