"""第二階段擴充展示。由 B 建立 Analytics 拓樸後啟動。"""
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3


DB_PATH = Path(__file__).resolve().parents[1] / "runtime" / "analytics.sqlite3"


def record_order(event_id, amount, db_path):
    """以 event_id 主鍵保存一次訂單事件，並讀取累計結果。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS orders "
            "(event_id TEXT PRIMARY KEY, total_amount TEXT NOT NULL)"
        )
        inserted = connection.execute(
            "INSERT INTO orders (event_id, total_amount) VALUES (?, ?) "
            "ON CONFLICT(event_id) DO NOTHING",
            (event_id, amount),
        ).rowcount == 1
        amounts = connection.execute("SELECT total_amount FROM orders").fetchall()
        total = sum((Decimal(row[0]) for row in amounts), Decimal("0.00"))
    return inserted, len(amounts), total


def handle_event(event, *, db_path=DB_PATH):
    from common.event_schema import validate_order_created

    validate_order_created(event)
    event_id = event["event_id"]
    inserted, count, total = record_order(event_id, event["data"]["total_amount"], db_path)
    status = "RECORDED" if inserted else "DUPLICATE"
    print(f"[{status}] {event_id} | 訂單筆數 {count} | 訂單金額 TWD {total:.2f}", flush=True)


def main():
    from common.config import QUEUES

    queue_name = QUEUES.get("analytics")
    if queue_name != "analytics.order-created":
        raise SystemExit("請先由 B 加入 Analytics Queue、Binding、DLQ 與 QUEUES 設定。")

    from common.messaging import consume_events

    consume_events(queue_name, handle_event)


if __name__ == "__main__":
    main()
