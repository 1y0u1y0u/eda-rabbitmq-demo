"""Cross-service checks using the real E, C, D and B code at the Pika boundary."""
import json
import os
import re
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from app import create_app


class IntegrationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = patch.dict(os.environ, {
            "RABBITMQ_USER": "offline_test",
            "RABBITMQ_PASSWORD": "offline_test",
        })
        cls.config.start()
        cls.addClassCleanup(cls.config.stop)

    def setUp(self):
        from common import messaging
        from services import inventory_service, notification_service, payment_service

        self.messaging = messaging
        self.inventory = inventory_service
        self.notification = notification_service
        self.payment = payment_service
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.products = self.root / "products.json"
        copyfile(inventory_service.PRODUCTS_FILE, self.products)
        self.client = create_app(runtime_dir=self.root).test_client()
        page = self.client.get("/").get_data(as_text=True)
        self.token = re.search(r'name="form_token" value="([^"]+)"', page)[1]

    def publish(self, quantity=2):
        connection = Mock()
        with patch.object(self.messaging, "get_connection", return_value=connection):
            result = self.client.post("/orders", data={
                "form_token": self.token, "product_id": "P001",
                "quantity": str(quantity), "unit_price": "500.00",
            })
        self.assertEqual(result.status_code, 303)
        channel = connection.channel.return_value
        channel.confirm_delivery.assert_called_once()
        channel.basic_publish.assert_called_once()
        sent = channel.basic_publish.call_args.kwargs
        event = json.loads(sent["body"])
        self.assertTrue(sent["mandatory"])
        self.assertEqual(sent["exchange"], self.messaging.EXCHANGE_NAME)
        self.assertEqual(sent["routing_key"], self.messaging.ROUTING_KEY)
        self.assertEqual(sent["properties"].message_id, event["event_id"])
        self.assertEqual(event["data"]["total_amount"], f"{500 * quantity}.00")
        page = self.client.get(result.location).get_data(as_text=True)
        self.assertIn(event["event_id"], page)
        self.assertIn(event["data"]["order_id"], page)
        self.assertIn("RabbitMQ 已確認發布", page)
        return event["event_id"], sent["body"]

    def consume(self, service, handler, body, *, ack=True):
        connection = Mock()
        channel = connection.channel.return_value
        delivery = SimpleNamespace(delivery_tag=7, redelivered=False)

        def deliver():
            callback = channel.basic_consume.call_args.kwargs["on_message_callback"]
            callback(channel, delivery, None, body)

        channel.start_consuming.side_effect = deliver
        with patch.object(self.messaging, "get_connection", return_value=connection):
            self.messaging.consume_events(self.messaging.QUEUES[service], handler, once=True)
        if ack:
            channel.basic_ack.assert_called_once_with(delivery_tag=7)
            channel.basic_nack.assert_not_called()
        else:
            channel.basic_nack.assert_called_once_with(delivery_tag=7, requeue=False)
            channel.basic_ack.assert_not_called()

    def inventory_handler(self, event):
        self.inventory.process_order_created(event, inventory_file=self.products)

    def payment_handler(self, event, *, mode="success"):
        self.payment.handle_event(event, mode=mode, db_path=self.root / "payment.sqlite3")

    def notification_handler(self, event):
        self.notification.handle_event(event, db_path=self.root / "notification.sqlite3")

    def stock(self):
        state = json.loads(self.products.read_text(encoding="utf-8"))
        return next(p["stock"] for p in state["products"] if p["product_id"] == "P001")

    def lookup(self, event_id):
        return self.client.get("/", query_string={"event_id": event_id}).get_data(as_text=True)

    def test_same_event_reaches_all_handlers_and_deduplicates(self):
        before = self.stock()
        event_id, body = self.publish()
        handlers = (
            ("inventory", self.inventory_handler),
            ("payment", self.payment_handler),
            ("notification", self.notification_handler),
        )
        for name, handler in handlers[:2]:
            self.consume(name, handler, body)
        self.assertIn("付款 · 成功", self.lookup(event_id))
        self.assertNotIn("通知 · 已記錄", self.lookup(event_id))
        self.consume(*handlers[2], body)
        self.assertIn("通知 · 已記錄", self.lookup(event_id))
        self.assertEqual(self.stock(), before - 2)

        for name, handler in handlers:
            self.consume(name, handler, body)
        self.assertEqual(self.stock(), before - 2)
        for name, initial_status in (("payment", "SUCCESS"), ("notification", "RECORDED")):
            entries = (self.root / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual([json.loads(entry)["status"] for entry in entries],
                             [initial_status, "DUPLICATE"])
        print(f"E integration evidence: {event_id} stock {before} -> {before - 2}")

    def test_decline_acks_and_technical_failure_nacks(self):
        declined_id, declined = self.publish()
        self.consume("payment", lambda event: self.payment_handler(event, mode="decline"),
                     declined)
        self.assertIn("付款遭拒", self.lookup(declined_id))

        error_id, failed = self.publish()
        self.consume("payment", lambda event: self.payment_handler(event, mode="error"),
                     failed, ack=False)
        self.assertIn("尚未查到已保存的結果", self.lookup(error_id))
        entries = (self.root / "payment.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(entries[-1])["status"], "ERROR")

    def test_current_inventory_shortage_nacks_without_changing_stock(self):
        """Record the observed behavior until the team agrees on the contract."""
        before = self.stock()
        _, body = self.publish(quantity=before + 1)
        self.consume("inventory", self.inventory_handler, body, ack=False)
        self.assertEqual(self.stock(), before)
