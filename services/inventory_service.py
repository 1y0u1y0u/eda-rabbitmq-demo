
import json
import os
import tempfile
from pathlib import Path

from common.config import QUEUES
from common.event_schema import validate_order_created
from common.messaging import consume_events


# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 商品庫存資料檔案
PRODUCTS_FILE = PROJECT_ROOT / "data" / "products.json"


# 讀取商品庫存
def load_inventory(inventory_file=PRODUCTS_FILE):
    """
    讀取商品庫存資料。
    如果商品尚未有 stock 欄位，
    就使用 initial_stock 作為目前庫存。
    """

    with open(inventory_file, "r", encoding="utf-8") as file:
        inventory = json.load(file)

    if not isinstance(inventory.get("products"), list):
        raise ValueError("products 必須是清單")

    inventory.setdefault("processed_event_ids", [])
    inventory.setdefault("processing_results", [])

    if not isinstance(inventory["processed_event_ids"], list):
        raise ValueError("processed_event_ids 必須是清單")

    if not isinstance(inventory["processing_results"], list):
        raise ValueError("processing_results 必須是清單")

    for product in inventory["products"]:
        product.setdefault("stock", product["initial_stock"])

    return inventory


# 儲存更新後的庫存
def save_inventory(inventory, inventory_file=PRODUCTS_FILE):
    """
    原子性寫入庫存資料。
    避免程式寫入中途失敗造成 JSON 檔案損壞。
    """

    inventory_file = Path(inventory_file)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=inventory_file.parent,
            suffix=".tmp",
            delete=False
        ) as file:

            temp_path = file.name

            json.dump(
                inventory,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(temp_path, inventory_file)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# 處理訂單事件
def process_order_created(event, inventory_file=PRODUCTS_FILE):
    """
    處理 OrderCreated 事件。

    1. 驗證事件格式
    2. 讀取庫存
    3. 防止重複事件
    4. 找到商品
    5. 檢查庫存
    6. 庫存不足：保存業務拒絕結果並正常返回
    7. 庫存足夠：扣除庫存並保存結果
    """

    # 1. 驗證事件格式
    validate_order_created(event)

    event_id = event["event_id"]
    data = event["data"]

    order_id = data["order_id"]
    product_id = data["product_id"]
    quantity = data["quantity"]

    print("\n===== Inventory Service =====")
    print("收到訂單：", order_id)
    print("商品編號：", product_id)
    print("購買數量：", quantity)

    # 2. 讀取庫存
    inventory = load_inventory(inventory_file)

    # 3. 防止重複處理
    if event_id in inventory["processed_event_ids"]:
        print("[DUPLICATE] 此事件已處理，不重複扣庫存")
        return "duplicate"

    # 4. 搜尋商品
    product = next(
        (
            item for item in inventory["products"]
            if item["product_id"] == product_id
        ),
        None
    )

    if product is None:
        raise ValueError(f"找不到商品：{product_id}")

    current_stock = product["stock"]

    print("商品名稱：", product["product_name"])
    print("目前庫存：", current_stock)

    # 5. 檢查庫存是否足夠
    if current_stock < quantity:

        rejection_reason = (
            f"庫存不足！目前庫存：{current_stock}，"
            f"需要數量：{quantity}"
        )

        # 保存業務拒絕結果
        inventory["processing_results"].append({
            "event_id": event_id,
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "status": "rejected",
            "reason": rejection_reason
        })

        # 即使業務拒絕，也要記錄 event_id
        # 避免補貨後相同事件再次扣庫存
        inventory["processed_event_ids"].append(event_id)

        # 保存拒絕結果及去重紀錄
        save_inventory(inventory, inventory_file)

        print("[REJECTED] 庫存不足，訂單不予處理")
        print("拒絕原因：", rejection_reason)
        print("目前庫存維持：", current_stock)

        # 正常返回，讓共用 Consumer 執行 ACK
        return "rejected"

    # 6. 庫存足夠，扣除庫存
    product["stock"] -= quantity

    # 7. 記錄已處理事件
    inventory["processed_event_ids"].append(event_id)

    # 保存成功結果
    inventory["processing_results"].append({
        "event_id": event_id,
        "order_id": order_id,
        "product_id": product_id,
        "quantity": quantity,
        "status": "processed",
        "reason": None
    })

    # 8. 儲存資料
    save_inventory(inventory, inventory_file)

    print("[SUCCESS] 庫存扣除成功")
    print("扣除數量：", quantity)
    print("剩餘庫存：", product["stock"])

    return "processed"


def start_inventory_consumer():
    """
    啟動 Inventory Consumer。
    持續監聽 inventory.order-created Queue。
    """

    queue_name = QUEUES["inventory"]

    print("===== Inventory Consumer 啟動 =====")
    print("監聽 Queue：", queue_name)

    consume_events(
        queue_name=queue_name,
        handler=process_order_created
    )


if __name__ == "__main__":
    start_inventory_consumer()
