import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.config import load_services
from app.db import Database
from app.scheduler import run_forever


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(os.getenv("STATUSWATCH_DB", "statuswatch.db"))
    app.state.db = db

    task = None
    if os.getenv("STATUSWATCH_SCHEDULER", "1") != "0":
        services = load_services(os.getenv("STATUSWATCH_SERVICES", "services.json"))
        interval = float(os.getenv("STATUSWATCH_INTERVAL", "30"))
        task = asyncio.create_task(run_forever(services, db, interval))

    yield

    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    db.close()


app = FastAPI(title="StatusWatch", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return app.state.db.latest_per_service()


@app.get("/api/history")
def history(service: str, limit: int = 50):
    return app.state.db.recent(service, min(limit, 500))