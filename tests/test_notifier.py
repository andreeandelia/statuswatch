import json

import httpx

from app.notifier import WebhookNotifier, opened_message, resolved_message


def make_client(status: int, captured: list) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(status)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_discord_payload_uses_content_key():
    captured = []
    notifier = WebhookNotifier(
        "http://hook.test", "discord", client=make_client(204, captured)
    )
    assert await notifier.notify("hello") is True
    assert captured == [{"content": "hello"}]


async def test_slack_payload_uses_text_key():
    captured = []
    notifier = WebhookNotifier(
        "http://hook.test", "slack", client=make_client(200, captured)
    )
    assert await notifier.notify("hello") is True
    assert captured == [{"text": "hello"}]


async def test_http_error_returns_false_without_raising():
    notifier = WebhookNotifier("http://hook.test", client=make_client(500, []))
    assert await notifier.notify("hello") is False


def test_message_formats():
    assert "DOWN" in opened_message("api", "timeout")
    assert "api" in opened_message("api", "timeout")
    assert "RECOVERED" in resolved_message("api", "5m 2s")
    assert "5m 2s" in resolved_message("api", "5m 2s")