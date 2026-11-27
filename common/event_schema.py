
from decimal import Decimal, InvalidOperation


def validate_order_created(event):
    """驗證 OrderCreated 事件格式"""

    if not isinstance(event, dict):
        raise ValueError("event 必須是字典")

    required_fields = [
        "event_id",
        "event_type",
        "event_version",
        "occurred_at",
        "producer",
        "correlation_id",
        "data"
    ]

    for field in required_fields:
        if field not in event:
            raise ValueError(f"缺少欄位：{field}")

    if not isinstance(event["event_id"], str) or not event["event_id"].strip():
        raise ValueError("event_id 不可空白")

    if event["event_type"] != "OrderCreated":
        raise ValueError("event_type 必須是 OrderCreated")

    if event["event_version"] != 1:
        raise ValueError("event_version 必須是 1")

    if not isinstance(event["data"], dict):
        raise ValueError("data 必須是字典")

    data = event["data"]

    required_data = [
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "total_amount",
        "currency"
    ]

    for field in required_data:
        if field not in data:
            raise ValueError(f"data 缺少欄位：{field}")

    if not isinstance(data["order_id"], str) or not data["order_id"].strip():
        raise ValueError("order_id 不可空白")

    if not isinstance(data["product_id"], str) or not data["product_id"].strip():
        raise ValueError("product_id 不可空白")

    quantity = data["quantity"]

    if type(quantity) is not int or quantity <= 0:
        raise ValueError("quantity 必須是大於 0 的整數")

    try:
        unit_price = Decimal(str(data["unit_price"]))
        total_amount = Decimal(str(data["total_amount"]))

        if not unit_price.is_finite() or not total_amount.is_finite():
            raise ValueError("金額格式錯誤")

        if unit_price < 0:
            raise ValueError("unit_price 不可為負數")

        if total_amount != unit_price * quantity:
            raise ValueError("total_amount 計算錯誤")

    except InvalidOperation:
        raise ValueError("金額格式錯誤")

    if data["currency"] != "TWD":
        raise ValueError("currency 必須是 TWD")

    return None
