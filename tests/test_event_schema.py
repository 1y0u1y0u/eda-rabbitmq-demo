
from common.event_schema import validate_order_created


# 建立一筆合法訂單事件
event = {
    "event_id": "EVT001",
    "event_type": "OrderCreated",
    "event_version": 1,
    "occurred_at": "2026-11-25T14:00:00+08:00",
    "producer": "order_service",
    "correlation_id": "ORD001",
    "data": {
        "order_id": "ORD001",
        "product_id": "P001",
        "quantity": 2,
        "unit_price": "500.00",
        "total_amount": "1000.00",
        "currency": "TWD"
    }
}


# 測試一：合法事件
print("===== 測試一：合法事件 =====")

try:
    result = validate_order_created(event)

    assert result is None
    print("PASS：合法事件驗證成功")

except ValueError as error:
    print("FAIL：", error)


# 測試二：錯誤數量
print("\n===== 測試二：錯誤數量 =====")

invalid_event = event.copy()
invalid_event["data"] = event["data"].copy()
invalid_event["data"]["quantity"] = 0

try:
    validate_order_created(invalid_event)
    print("FAIL：錯誤數量沒有被攔截")

except ValueError as error:
    print("PASS：成功攔截錯誤數量")
    print("錯誤原因：", error)


# 測試三：錯誤事件類型
print("\n===== 測試三：錯誤事件類型 =====")

invalid_type_event = event.copy()
invalid_type_event["event_type"] = "PaymentCompleted"

try:
    validate_order_created(invalid_type_event)
    print("FAIL：錯誤事件類型沒有被攔截")

except ValueError as error:
    print("PASS：成功攔截錯誤事件類型")
    print("錯誤原因：", error)

