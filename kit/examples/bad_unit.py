"""Deliberately broken example: what an agent writes when nobody checks."""
import time


def sync_orders(orders, client):
    results = []
    for order in orders:
        if order.get("paid"):
            if order.get("country") == "KR" and order.get("total", 0) > 0:
                try:
                    results.append(client.ship(order))
                except:
                    pass
            elif order.get("retry"):
                time.sleep(5)
                results.append(client.ship(order))
    return results
