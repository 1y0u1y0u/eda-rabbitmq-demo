
import json
import shutil
import tempfile
import unittest

from pathlib import Path

from services.inventory_service import process_order_created


class TestInventoryService(unittest.TestCase):

    def setUp(self):
        # 建立獨立測試資料，不修改正式 products.json
        self.temp_dir = tempfile.TemporaryDirectory()

        self.inventory_file = Path(
            self.temp_dir.name
        ) / "products.json"

        source_file = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "products.json"
        )

        shutil.copyfile(source_file, self.inventory_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_event(
        self,
        event_id="EVT_TEST_001",
        product_id="P001",
        quantity=2
    ):
        return {
            "event_id": event_id,
            "event_type": "OrderCreated",
            "event_version": 1,
            "occurred_at": "2026-11-28T02:00:00+08:00",
            "producer": "order_service",
            "correlation_id": "ORD_TEST_001",
            "data": {
                "order_id": "ORD_TEST_001",
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": "500.00",
                "total_amount": f"{500 * quantity:.2f}",
                "currency": "TWD"
            }
        }

    def get_inventory(self):
        with open(
            self.inventory_file,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    def get_stock(self, product_id="P001"):
        inventory = self.get_inventory()

        product = next(
            p for p in inventory["products"]
            if p["product_id"] == product_id
        )

        return product.get(
            "stock",
            product["initial_stock"]
        )

    def set_stock(self, stock, product_id="P001"):
        """
        模擬補充庫存。
        保留原本的 event_id 去重紀錄。
        """

        inventory = self.get_inventory()

        product = next(
            p for p in inventory["products"]
            if p["product_id"] == product_id
        )

        product["stock"] = stock

        with open(
            self.inventory_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                inventory,
                file,
                ensure_ascii=False,
                indent=4
            )

    # 測試一：正常扣除庫存
    def test_successful_deduction(self):

        event = self.create_event()

        result = process_order_created(
            event,
            self.inventory_file
        )

        self.assertEqual(result, "processed")
        self.assertEqual(self.get_stock(), 8)

        inventory = self.get_inventory()

        self.assertIn(
            "EVT_TEST_001",
            inventory["processed_event_ids"]
        )

        print("\nPASS：正常扣除庫存")

    # 測試二：重複事件不能重複扣庫存
    def test_duplicate_event(self):

        event = self.create_event()

        process_order_created(
            event,
            self.inventory_file
        )

        result = process_order_created(
            event,
            self.inventory_file
        )

        self.assertEqual(result, "duplicate")
        self.assertEqual(self.get_stock(), 8)

        print("\nPASS：成功阻止重複扣庫存")

    # 測試三：庫存不足，保存拒絕結果並正常返回
    def test_insufficient_stock(self):

        event = self.create_event(quantity=11)

        result = process_order_created(
            event,
            self.inventory_file
        )

        self.assertEqual(result, "rejected")

        # 庫存不應被扣除
        self.assertEqual(self.get_stock(), 10)

        inventory = self.get_inventory()

        # 庫存不足也必須記錄 event_id
        self.assertIn(
            "EVT_TEST_001",
            inventory["processed_event_ids"]
        )

        # 確認業務拒絕結果有被保存
        rejection = next(
            item for item in inventory["processing_results"]
            if item["event_id"] == "EVT_TEST_001"
        )

        self.assertEqual(rejection["status"], "rejected")
        self.assertIn("庫存不足", rejection["reason"])

        print("\nPASS：庫存不足時成功保存拒絕結果")

    # 測試四：商品不存在
    def test_product_not_found(self):

        event = self.create_event(
            product_id="P999",
            quantity=1
        )

        with self.assertRaisesRegex(ValueError, "找不到商品"):
            process_order_created(
                event,
                self.inventory_file
            )

        print("\nPASS：成功辨識不存在的商品")

    # 測試五：庫存不足後補貨，相同事件不能再次扣庫存
    def test_duplicate_after_restock(self):

        event = self.create_event(
            event_id="EVT_TEST_005",
            quantity=11
        )

        # 第一次處理：庫存不足
        first_result = process_order_created(
            event,
            self.inventory_file
        )

        self.assertEqual(first_result, "rejected")
        self.assertEqual(self.get_stock(), 10)

        # 模擬補貨：庫存從 10 增加至 20
        self.set_stock(20)

        self.assertEqual(self.get_stock(), 20)

        # 第二次收到相同 event_id
        second_result = process_order_created(
            event,
            self.inventory_file
        )

        # 必須判定為重複事件
        self.assertEqual(second_result, "duplicate")

        # 不可因為補貨而重新扣除 11 件
        self.assertEqual(self.get_stock(), 20)

        inventory = self.get_inventory()

        # 去重紀錄仍然存在
        self.assertIn(
            "EVT_TEST_005",
            inventory["processed_event_ids"]
        )

        print("\nPASS：補貨後重送相同事件，不會再次扣庫存")


if __name__ == "__main__":
    unittest.main(verbosity=2)
