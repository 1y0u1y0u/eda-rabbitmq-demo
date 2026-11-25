
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pika

from common.config import QUEUES
from common.messaging import get_connection


def main():
    queue_name = QUEUES["inventory"]

    event = {
        "event_id": f"EVT-DLQ-{uuid4().hex}",
        "event_type": "OrderCreated",
        "event_version": 1,
        "occurred_at": datetime.now(
            timezone(timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "producer": "dlq_test",
        "correlation_id": "ORD-DLQ-TEST",
        "data": {
            # 故意缺少 order_id，模擬錯誤資料
            "product_id": "P001",
            "quantity": 2,
            "unit_price": "500.00",
            "total_amount": "1000.00",
            "currency": "TWD",
        },
    }

    connection = get_connection()

    try:
        channel = connection.channel()
        channel.confirm_delivery()

        # 使用 RabbitMQ 預設 Exchange，
        # 只將測試訊息送進 Inventory Queue。
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(
                event,
                ensure_ascii=False,
            ).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                content_encoding="utf-8",
                delivery_mode=2,
                message_id=event["event_id"],
                type=event["event_type"],
            ),
            mandatory=True,
        )

        print("錯誤測試事件發布成功")
        print(f"目標 Queue：{queue_name}")
        print(f"event_id：{event['event_id']}")
        print("故意缺少欄位：data.order_id")

    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
