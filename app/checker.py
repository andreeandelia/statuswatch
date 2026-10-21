import asyncio
import socket
import time
from dataclasses import dataclass

import httpx


@dataclass
class CheckResult:
    ok: bool
    latency_ms: float | None
    detail: str


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


async def check_http(
    url: str,
    timeout: float = 5.0,
    expected_status: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> CheckResult:
    """Verifică un URL. Fără expected_status, orice cod < 400 e considerat OK."""
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    start = time.perf_counter()
    try:
        response = await client.get(url)
        latency = _elapsed_ms(start)
        if expected_status is not None:
            ok = response.status_code == expected_status
        else:
            ok = response.status_code < 400
        return CheckResult(ok, latency, f"HTTP {response.status_code}")
    except httpx.TimeoutException:
        return CheckResult(False, None, "timeout")
    except httpx.HTTPError as exc:
        return CheckResult(False, None, f"error: {type(exc).__name__}")
    finally:
        if own_client:
            await client.aclose()


async def check_tcp(host: str, port: int, timeout: float = 5.0) -> CheckResult:
    """Verifică dacă se poate deschide o conexiune TCP."""
    start = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout
        )
        latency = _elapsed_ms(start)
        writer.close()
        await writer.wait_closed()
        return CheckResult(True, latency, "connected")
    except asyncio.TimeoutError:
        return CheckResult(False, None, "timeout")
    except OSError as exc:
        return CheckResult(False, None, f"error: {type(exc).__name__}")


async def check_dns(hostname: str, timeout: float = 5.0) -> CheckResult:
    """Verifică dacă un hostname se poate rezolva în adrese IP."""
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    try:
        infos = await asyncio.wait_for(loop.getaddrinfo(hostname, None), timeout)
        latency = _elapsed_ms(start)
        ips = sorted({info[4][0] for info in infos})
        return CheckResult(True, latency, f"resolved to {', '.join(ips)}")
    except asyncio.TimeoutError:
        return CheckResult(False, None, "timeout")
    except socket.gaierror:
        return CheckResult(False, None, "resolution failed")