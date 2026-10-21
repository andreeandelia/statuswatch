import asyncio

import httpx

from app.checker import check_dns, check_http, check_tcp


def make_client(status: int) -> httpx.AsyncClient:
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    return httpx.AsyncClient(transport=transport)


# ---------- HTTP ----------

async def test_http_ok():
    async with make_client(200) as client:
        result = await check_http("http://example.test", client=client)
    assert result.ok is True
    assert result.latency_ms is not None
    assert result.detail == "HTTP 200"


async def test_http_server_error_is_failure():
    async with make_client(500) as client:
        result = await check_http("http://example.test", client=client)
    assert result.ok is False
    assert result.detail == "HTTP 500"


async def test_http_expected_status():
    async with make_client(404) as client:
        result = await check_http(
            "http://example.test", expected_status=404, client=client
        )
    assert result.ok is True


async def test_http_timeout():
    def handler(request):
        raise httpx.ReadTimeout("too slow")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with client:
        result = await check_http("http://example.test", client=client)
    assert result.ok is False
    assert result.detail == "timeout"


# ---------- TCP ----------

async def test_tcp_open_port():
    async def handler(reader, writer):
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await check_tcp("127.0.0.1", port)
    finally:
        server.close()
        await server.wait_closed()
    assert result.ok is True
    assert result.latency_ms is not None


async def test_tcp_closed_port():
    async def handler(reader, writer):
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    result = await check_tcp("127.0.0.1", port, timeout=2.0)
    assert result.ok is False


# ---------- DNS ----------

async def test_dns_resolves_localhost():
    result = await check_dns("localhost")
    assert result.ok is True
    assert "resolved to" in result.detail


async def test_dns_invalid_host():
    result = await check_dns("does-not-exist.invalid")
    assert result.ok is False