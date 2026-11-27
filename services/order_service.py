
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pika

from common.event_schema import validate_order_created
from common.messaging import publish_event


# 台灣時區 UTC+8
TAIWAN_TZ = timezone(timedelta(hours=8))


def generate_order_id():
    """產生唯一訂單編號。"""
    return f"ORD{uuid.uuid4().hex[:12].upper()}"


def generate_event_id():
    """產生唯一事件編號。"""
    return f"EVT{uuid.uuid4().hex[:12].upper()}"


def create_order(product_id, quantity, unit_price):
    """
    建立訂單並發布 OrderCreated 事件。

    Parameters:
        product_id: 商品編號
        quantity: 購買數量
        unit_price: 商品單價

    Returns:
        dict: 訂單編號、事件編號及發布狀態
    """

    # =================================
    # 1. 驗證輸入資料
    # =================================

    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("product_id 不可為空")

    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValueError("quantity 必須是整數")

    if quantity <= 0:
        raise ValueError("quantity 必須大於 0")

    try:
        price = Decimal(str(unit_price))

        if not price.is_finite():
            raise ValueError("unit_price 必須是有效數字")

        if price < 0:
            raise ValueError("unit_price 不可為負數")

        price = price.quantize(
            # Decimal - 精確處理金額，避免浮點數誤差
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    except (InvalidOperation, ValueError):
        raise ValueError("unit_price 金額格式錯誤")

    # =================================
    # 2. 產生訂單與事件編號
    # =================================

    order_id = generate_order_id()
    event_id = generate_event_id()

    # =================================
    # 3. 計算訂單總金額
    # =================================

    total_amount = price * quantity

    # =================================
    # 4. 建立 OrderCreated 事件
    # =================================
    # datetime - 紀錄事件發生時間

    event = {
        "event_id": event_id,
        "event_type": "OrderCreated",
        "event_version": 1,
        "occurred_at": datetime.now(TAIWAN_TZ).isoformat(),
        "producer": "order_service",
        "correlation_id": order_id,
        "data": {
            "order_id": order_id,
            "product_id": product_id.strip(),
            "quantity": quantity,
            "unit_price": format(price, ".2f"),
            "total_amount": format(total_amount, ".2f"),
            "currency": "TWD"
        }
    }

    # =================================
    # 5. 驗證事件格式
    # =================================

    validate_order_created(event)

    # =================================
    # 6. 發布事件至 RabbitMQ
    # =================================
    # try / except - 區分發布失敗及結果不明

    try:
        publish_event(event)  # 將事件傳送到RabbitMQ

        print("[SUCCESS] 訂單事件發布成功")

        return {
            "order_id": order_id,
            "event_id": event_id,
            "publish_status": "confirmed"
        }

    except (
        pika.exceptions.UnroutableError,
        pika.exceptions.NackError,
    ) as error:

        print(f"[FAILED] RabbitMQ 拒絕發布：{error}")

        return {
            "order_id": order_id,
            "event_id": event_id,
            "publish_status": "failed",
            "error": str(error)
        }

    except Exception as error:

        # 無法確認 Broker 是否已收到訊息
        print(f"[UNKNOWN] 無法確認發布結果：{error}")

        return {
            "order_id": order_id,
            "event_id": event_id,
            "publish_status": "unknown",
            "error": str(error)
        }
