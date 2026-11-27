
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
    2. 防止重複事件
    3. 找到商品
    4. 檢查庫存
    5. 扣除庫存
    6. 儲存更新結果
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
        raise ValueError(
            f"庫存不足！目前庫存：{current_stock}，"
            f"需要數量：{quantity}"
        )

    # 6. 扣除庫存
    product["stock"] -= quantity

    # 7. 記錄已處理事件
    inventory["processed_event_ids"].append(event_id)

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
