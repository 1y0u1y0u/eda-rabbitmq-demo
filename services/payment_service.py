import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from functools import partial


DB_PATH = Path(__file__).resolve().parents[1] / "runtime" / "payment.sqlite3"


def write_log(db_path, event, status, detail):
    data = event.get("data")
    entry = {
        "service": "payment",
        "event_id": event.get("event_id"),
        "order_id": data.get("order_id") if isinstance(data, dict) else None,
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "detail": detail,
    }
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with db_path.with_suffix(".jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle_event(event, *, mode="success", db_path=DB_PATH):
    try:
        status, detail = process_event(event, db_path=db_path, mode=mode)
    except Exception as exc:
        write_log(db_path, event, "ERROR", f"{type(exc).__name__}: {exc}")
        raise
    write_log(db_path, event, status, detail)


def process_event(event, *, mode="success", db_path=DB_PATH):
    event_id = event.get("event_id")
    data = event.get("data")
    if event.get("event_type") != "OrderCreated" or type(event.get("event_version")) is not int or event["event_version"] != 1:
        raise ValueError("Expected OrderCreated version 1")
    if not isinstance(data, dict):
        raise ValueError("Missing order data")
    order_id = data.get("order_id")
    amount = data.get("total_amount")
    currency = data.get("currency")
    fields = (event_id, order_id, amount, currency)
    if not all(isinstance(value, str) and value.strip() for value in fields):
        raise ValueError(f"Invalid payment fields: event_id={event_id!r}, order_id={order_id!r}")
    try:
        total = Decimal(amount)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount for {event_id}: {amount!r}") from exc
    if not total.is_finite() or total < 0:
        raise ValueError(f"Invalid amount for {event_id}: {amount!r}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    processed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(sqlite3.connect(db_path, timeout=10)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""
            CREATE TABLE IF NOT EXISTS results (
                event_id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
                processed_at TEXT NOT NULL, status TEXT NOT NULL,
                total_amount TEXT NOT NULL, currency TEXT NOT NULL, detail TEXT NOT NULL
            )
        """)
        existing = db.execute("SELECT status FROM results WHERE event_id = ?", (event_id,)).fetchone()
        if existing:
            print(f"{processed_at} payment {event_id} {order_id} DUPLICATE original={existing[0]}")
            return "DUPLICATE", f"original={existing[0]}"
        if mode == "error":
            raise RuntimeError(f"{processed_at} payment {event_id} {order_id} simulated technical error")
        if mode not in ("success", "decline"):
            raise ValueError(f"Unknown payment mode: {mode}")
        status = "SUCCESS" if mode == "success" else "DECLINED"
        detail = "模擬付款成功" if mode == "success" else "模擬付款遭拒"

        db.execute(
            "INSERT INTO results (event_id, order_id, processed_at, status, total_amount, currency, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, order_id, processed_at, status, amount, currency, detail),
        )
    print(f"{processed_at} payment {event_id} {order_id} {status} {currency} {amount} {detail}")
    return status, detail


def main():
    parser = argparse.ArgumentParser(description="payment OrderCreated consumer")
    parser.add_argument("--mode", choices=("success", "decline", "error"), default="success")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--ack-delay", type=int, default=0, choices=range(121), metavar="0..120")
    args = parser.parse_args()
    from common.config import QUEUES
    from common.messaging import consume_events

    consume_events(
        QUEUES["payment"], partial(handle_event, mode=args.mode),
        once=args.once, ack_delay=args.ack_delay,
    )


if __name__ == "__main__":
    main()
