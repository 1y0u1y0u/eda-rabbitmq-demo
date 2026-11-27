
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

    def get_stock(self, product_id="P001"):
        with open(
            self.inventory_file,
            "r",
            encoding="utf-8"
        ) as file:
            inventory = json.load(file)

        product = next(
            p for p in inventory["products"]
            if p["product_id"] == product_id
        )

        return product.get(
            "stock",
            product["initial_stock"]
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

    # 測試三：庫存不足
    def test_insufficient_stock(self):

        event = self.create_event(quantity=11)

        with self.assertRaisesRegex(ValueError, "庫存不足"):
            process_order_created(
                event,
                self.inventory_file
            )

        self.assertEqual(self.get_stock(), 10)

        print("\nPASS：成功阻止超額購買")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
