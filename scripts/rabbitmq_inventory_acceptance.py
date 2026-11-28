"""Run from an isolated demo copy after setup_rabbitmq and with consumers stopped."""
import json
from contextlib import closing
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from unittest.mock import patch

import pika

from common.config import QUEUES
from common.messaging import consume_events, get_connection
from services import inventory_service, order_service


def run(products_path, channel):
    queue = QUEUES["inventory"]
    dlq = f"{queue}.dlq"

    def ready(name, expected):
        deadline = monotonic() + 5
        while True:
            state = channel.queue_declare(queue=name, passive=True).method
            if state.consumer_count:
                raise RuntimeError(f"Stop other consumers on {name} before running this test")
            if state.message_count == expected:
                return
            if monotonic() >= deadline:
                raise AssertionError(f"{name}: wanted {expected}, got {state.message_count}")
            sleep(0.1)

    def stock():
        state = json.loads(products_path.read_text(encoding="utf-8"))
        return next(row["stock"] for row in state["products"] if row["product_id"] == "P001")

    def consume(event, dead_letters=0):
        # Send only to Inventory so Payment and Notification stay untouched.
        channel.basic_publish(
            exchange="", routing_key=queue, body=json.dumps(event).encode("utf-8"),
            properties=pika.BasicProperties(content_type="application/json",
                                            message_id=event["event_id"]),
            mandatory=True,
        )
        ready(queue, 1)
        consume_events(queue, lambda event: inventory_service.process_order_created(
            event, inventory_file=products_path), once=True)
        ready(queue, 0)
        ready(dlq, dead_letters)

    def new_order(quantity):
        with patch.object(order_service, "publish_event") as capture:
            result = order_service.create_order("P001", quantity, "500.00")
        capture.assert_called_once()
        event = capture.call_args.args[0]
        if event["event_id"] != result["event_id"]:
            raise AssertionError("Order Service returned the wrong event ID")
        return event

    ready(queue, 0)
    ready(dlq, 0)
    channel.confirm_delivery()
    before = stock()
    requested = before + 1
    shortage = new_order(requested)
    consume(shortage)
    if stock() != before:
        raise AssertionError("Insufficient-stock rejection changed stock")
    print(f"PASS {shortage['event_id']}: shortage consumed, stock {before}, DLQ empty")

    state = json.loads(products_path.read_text(encoding="utf-8"))
    product = next(row for row in state["products"] if row["product_id"] == "P001")
    product["stock"] = requested + 3
    products_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    consume(shortage)
    if stock() != requested + 3:
        raise AssertionError("Replay of rejected event deducted stock after replenishment")
    print(f"PASS {shortage['event_id']}: replay after replenishment did not deduct stock")

    fresh = new_order(requested)
    consume(fresh)
    if stock() != 3:
        raise AssertionError("A valid new event did not deduct stock")
    print(f"PASS {fresh['event_id']}: new event deducted stock")

    malformed = new_order(1)
    malformed["data"]["quantity"] = 0
    consume(malformed, dead_letters=1)
    method, _, body = channel.basic_get(dlq, auto_ack=False)
    if method is None or json.loads(body)["event_id"] != malformed["event_id"]:
        raise AssertionError("Wrong event in inventory DLQ")
    if stock() != 3:
        raise AssertionError("Malformed event changed stock")
    channel.basic_ack(method.delivery_tag)
    ready(dlq, 0)
    print(f"PASS {malformed['event_id']}: format error reached inventory DLQ")


def main():
    with TemporaryDirectory() as folder, closing(get_connection()) as connection:
        products_path = Path(folder) / "products.json"
        copyfile(inventory_service.PRODUCTS_FILE, products_path)
        run(products_path, connection.channel())


if __name__ == "__main__":
    main()
