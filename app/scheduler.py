import asyncio
import logging

from app.checker import CheckResult, check_dns, check_http, check_tcp
from app.config import Service
from app.db import Database

logger = logging.getLogger("statuswatch")


async def run_check(service: Service) -> CheckResult:
    if service.type == "http":
        return await check_http(service.target, expected_status=service.expected_status)
    if service.type == "tcp":
        return await check_tcp(service.target, service.port or 80)
    if service.type == "dns":
        return await check_dns(service.target)
    return CheckResult(False, None, f"unknown type: {service.type}")


async def run_cycle(services: list[Service], db: Database) -> None:
    """Rulează toate verificările în paralel și salvează rezultatele."""
    results = await asyncio.gather(*(run_check(s) for s in services))
    for service, result in zip(services, results):
        db.save_check(service.name, result)


async def run_forever(services: list[Service], db: Database, interval: float) -> None:
    while True:
        try:
            await run_cycle(services, db)
        except Exception:
            logger.exception("check cycle failed")
        await asyncio.sleep(interval)