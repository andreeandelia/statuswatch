import logging

import httpx

logger = logging.getLogger("statuswatch")


def opened_message(service: str, detail: str) -> str:
    return f"🔴 DOWN: {service} ({detail})"


def resolved_message(service: str, duration: str) -> str:
    return f"🟢 RECOVERED: {service} (down for {duration})"


class WebhookNotifier:
    """Trimite alerte la un webhook Discord sau Slack."""

    def __init__(
        self,
        url: str,
        kind: str = "discord",
        timeout: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.url = url
        self.kind = kind.lower()
        self.timeout = timeout
        self._client = client

    def payload(self, text: str) -> dict:
        key = "text" if self.kind == "slack" else "content"
        return {key: text}

    async def notify(self, text: str) -> bool:
        """Trimite mesajul. Nu aruncă niciodată excepții: o alertă eșuată
        nu trebuie să oprească monitorizarea."""
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await client.post(self.url, json=self.payload(text))
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            logger.error("webhook rejected alert: HTTP %s", exc.response.status_code)
        except httpx.HTTPError as exc:
            logger.error("webhook failed: %s", type(exc).__name__)
        finally:
            if self._client is None:
                await client.aclose()
        return False


if __name__ == "__main__":
    # Test rapid: python -m app.notifier
    import asyncio
    import os

    url = os.getenv("STATUSWATCH_WEBHOOK_URL")
    if not url:
        raise SystemExit("Set STATUSWATCH_WEBHOOK_URL first.")
    notifier = WebhookNotifier(url, os.getenv("STATUSWATCH_WEBHOOK_KIND", "discord"))
    ok = asyncio.run(notifier.notify("✅ StatusWatch test alert"))
    print("sent" if ok else "FAILED (see log above)")