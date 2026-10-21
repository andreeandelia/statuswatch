import asyncio
import logging

from app.checker import CheckResult, check_dns, check_http, check_tcp
from app.config import Service
from app.db import Database
from app.incidents import update_incidents
from app.notifier import opened_message, resolved_message
from app.utils import format_duration

logger = logging.getLogger("statuswatch")


async def run_check(service: Service) -> CheckResult:
    if service.type == "http":
        return await check_http(service.target, expected_status=service.expected_status)
    if service.type == "tcp":
        return await check_tcp(service.target, service.port or 80)
    if service.type == "dns":
        return await check_dns(service.target)
    return CheckResult(False, None, f"unknown type: {service.type}")


async def run_cycle(
    services: list[Service],
    db: Database,
    failure_threshold: int = 3,
    notifier=None,
) -> None:
    """Rulează verificările în paralel, salvează rezultatele, gestionează incidentele
    și trimite alerte (dacă există un notifier)."""
    results = await asyncio.gather(*(run_check(s) for s in services))
    for service, result in zip(services, results):
        db.save_check(service.name, result)
        event = update_incidents(db, service.name, failure_threshold)

        if event == "opened":
            logger.warning("INCIDENT OPENED: %s (%s)", service.name, result.detail)
            if notifier:
                await notifier.notify(opened_message(service.name, result.detail))
        elif event == "resolved":
            logger.warning("INCIDENT RESOLVED: %s", service.name)
            if notifier:
                incident = db.last_incident(service.name)
                duration = format_duration(
                    incident["resolved_at"] - incident["started_at"]
                )
                await notifier.notify(resolved_message(service.name, duration))


async def run_forever(
    services: list[Service],
    db: Database,
    interval: float,
    failure_threshold: int = 3,
    notifier=None,
) -> None:
    while True:
        try:
            await run_cycle(services, db, failure_threshold, notifier)
        except Exception:
            logger.exception("check cycle failed")
        await asyncio.sleep(interval)