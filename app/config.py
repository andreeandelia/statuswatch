import json
from dataclasses import dataclass


@dataclass
class Service:
    name: str
    type: str  # "http", "tcp" sau "dns"
    target: str
    port: int | None = None
    expected_status: int | None = None


def load_services(path: str) -> list[Service]:
    with open(path, encoding="utf-8") as f:
        return [Service(**item) for item in json.load(f)]