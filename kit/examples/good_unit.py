"""The same job split into small, checkable units."""
import time
from typing import Protocol


class Carrier(Protocol):
    def ship(self, order: dict) -> dict: ...


def should_ship(order: dict) -> bool:
    return bool(order.get("paid")) and order.get("country") == "KR" and order.get("total", 0) > 0


def ship_one(order: dict, client: Carrier, log: list[str]) -> dict | None:
    try:
        return client.ship(order)
    except ConnectionError as err:
        log.append(f"order {order.get('id')}: {err}")
        return None


def sync_orders(orders: list[dict], client: Carrier, log: list[str]) -> list[dict]:
    shipped = [ship_one(o, client, log) for o in orders if should_ship(o)]
    return [s for s in shipped if s is not None]


def backoff(attempt: int) -> None:
    time.sleep(min(2 ** attempt, 30))  # rate-limit: carrier API allows 1 call per second
