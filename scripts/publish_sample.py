import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from common.config import EXCHANGE_NAME, ROUTING_KEY
from common.messaging import publish_event


def build_sample_event():
    """建立符合目前共用格式的測試訂單事件。"""

    order_id = f"ORD-{uuid4().hex}"
    event_id = f"EVT-{uuid4().hex}"

    quantity = 2
    unit_price = Decimal("500.00")
    total_amount = unit_price * quantity

    taipei_timezone = timezone(timedelta(hours=8))

    return {
        "event_id": event_id,
        "event_type": "OrderCreated",
        "event_version": 1,
        "occurred_at": datetime.now(
            taipei_timezone
        ).isoformat(timespec="seconds"),
        "producer": "order_service",
        "correlation_id": order_id,
        "data": {
            "order_id": order_id,
            "product_id": "P001",
            "quantity": quantity,
            "unit_price": format(unit_price, ".2f"),
            "total_amount": format(total_amount, ".2f"),
            "currency": "TWD",
        },
    }


def main():
    event = build_sample_event()

    print("即將發布以下測試事件：")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    print()

    publish_event(event)

    # 只有 publish_event 正常返回，才會顯示這些訊息。
    print("發布完成：RabbitMQ 已確認，且未回報無法路由。")
    print(f"Exchange：{EXCHANGE_NAME}")
    print(f"Routing Key：{ROUTING_KEY}")
    print(f"event_id：{event['event_id']}")
    print(f"order_id：{event['data']['order_id']}")
    print()
    print("請確認三個主 Queue 的 Ready 是否各增加 1。")


if __name__ == "__main__":
    main()