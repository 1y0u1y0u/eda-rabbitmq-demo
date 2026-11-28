import re
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from app import create_app
from services.analytics_service import record_order


class OrderPageTest(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.runtime_dir = Path(temporary.name)
        self.create_order = Mock()
        self.client = create_app(self.create_order, self.runtime_dir).test_client()
        page = self.client.get("/").get_data(as_text=True)
        self.form_token = re.search(r'name="form_token" value="([^"]+)"', page)[1]

    def submit(self, **overrides):
        fields = {
            "product_id": " P001 ", "quantity": "2", "unit_price": "500.005",
            "form_token": self.form_token,
        }
        response = self.client.post("/orders", data=fields | overrides)
        self.assertEqual(response.status_code, 303)
        return self.client.get(response.location).get_data(as_text=True)

    def set_status(self, status):
        self.create_order.return_value = {
            "publish_status": status, "order_id": "ORD001", "event_id": "EVT001",
            "error": "測試原因" if status != "confirmed" else "",
        }

    def test_confirmed_and_refresh_does_not_publish_again(self):
        self.set_status("confirmed")
        page = self.submit()
        self.assertIn("RabbitMQ 已確認發布", page)
        self.assertIn("ORD001", page)
        self.assertIn("EVT001", page)
        self.assertNotIn("付款 · 成功", page)
        self.client.get("/")
        self.create_order.assert_called_once_with("P001", 2, "500.005")

    def test_failed_displays_error_and_ids(self):
        self.set_status("failed")
        page = self.submit()
        for text in ("事件發布失敗", "測試原因", "ORD001", "EVT001"):
            self.assertIn(text, page)

    def test_unknown_displays_ids_and_does_not_retry(self):
        self.set_status("unknown")
        page = self.submit()
        for text in ("無法確認發布結果", "請先查詢事件紀錄", "ORD001", "EVT001"):
            self.assertIn(text, page)
        self.client.get("/?event_id=EVT001")
        self.create_order.assert_called_once()

    def test_non_integer_quantity_stops_at_form(self):
        page = self.submit(quantity="1.5")
        self.assertIn("輸入資料有誤", page)
        self.create_order.assert_not_called()

    def test_validation_error_from_c(self):
        self.create_order.side_effect = ValueError("unit_price 金額格式錯誤")
        page = self.submit(unit_price="-1")
        self.assertIn("輸入資料有誤", page)
        self.assertIn("unit_price 金額格式錯誤", page)
        self.create_order.assert_called_once_with("P001", 2, "-1")

    def test_malformed_result_is_not_shown_as_success(self):
        self.create_order.return_value = {"publish_status": "confirmed"}
        page = self.submit()
        self.assertIn("無法確認發布結果", page)
        self.assertNotIn("RabbitMQ 已確認發布", page)

    def test_missing_token_is_rejected(self):
        self.assertEqual(self.client.post("/orders").status_code, 400)
        self.create_order.assert_not_called()

    def test_query_reads_only_matching_service_rows(self):
        for service, status, detail in (
            ("payment", "DECLINED", "模擬付款遭拒"),
            ("notification", "SUCCESS", "訂單已建立 & 待處理"),
        ):
            path = self.runtime_dir / f"{service}.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute(
                    "CREATE TABLE results (event_id, order_id, status, detail, processed_at)"
                )
                db.executemany(
                    "INSERT INTO results VALUES (?, ?, ?, ?, ?)",
                    [
                        ("EVT001", "ORD001", status, detail, "2026-11-28T04:00+00:00"),
                        ("EVT002", "ORD002", status, "其他事件", "2026-11-28T04:00+00:00"),
                    ],
                )

        page = self.client.get("/?event_id=EVT001").get_data(as_text=True)
        self.assertIn("付款 · 付款遭拒", page)
        self.assertIn("訂單已建立 &amp; 待處理", page)
        self.assertNotIn("其他事件", page)
        self.assertNotIn("ORD002", page)
        self.create_order.assert_not_called()

    def test_lookup_does_not_create_missing_runtime_files(self):
        page = self.client.get("/?event_id=EVT001").get_data(as_text=True)
        self.assertIn("尚未查到已保存的結果", page)
        self.assertEqual(list(self.runtime_dir.iterdir()), [])


class AnalyticsTest(TestCase):
    def test_duplicate_id_survives_reopen_and_does_not_inflate_total(self):
        with TemporaryDirectory() as directory:
            database = Path(directory) / "runtime" / "analytics.sqlite3"
            self.assertEqual(record_order("EVT001", "0.10", database),
                             (True, 1, Decimal("0.10")))
            self.assertEqual(record_order("EVT001", "900.00", database),
                             (False, 1, Decimal("0.10")))
            self.assertEqual(record_order("EVT002", "0.20", database),
                             (True, 2, Decimal("0.30")))
