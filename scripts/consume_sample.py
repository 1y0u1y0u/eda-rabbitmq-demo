import argparse
import json

from common.config import QUEUES
from common.messaging import consume_events


def handle_sample_event(event):
    """只驗證基本欄位並顯示事件，不執行真實業務。"""

    event_id = event.get("event_id")

    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("缺少有效的 event_id")

    if event.get("event_type") != "OrderCreated":
        raise ValueError("目前只接受 OrderCreated")

    data = event.get("data")

    if not isinstance(data, dict):
        raise ValueError("data 必須是物件")

    if not data.get("order_id"):
        raise ValueError("缺少 order_id")

    print(f"event_id：{event_id}")
    print(f"order_id：{data['order_id']}")
    print("事件內容：")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    print("測試處理完成：已讀取並顯示事件。")


def main():
    parser = argparse.ArgumentParser(
        description="RabbitMQ 測試接收者"
    )

    parser.add_argument(
        "--service",
        required=True,
        choices=list(QUEUES.keys()),
        help="選擇要接收的服務 Queue",
    )

    parser.add_argument(
        "--ack-delay",
        type=int,
        default=0,
        help="測試用：延遲幾秒送出 ACK，範圍 0～120",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="接收並處置一份訊息後結束",
    )

    args = parser.parse_args()

    if not 0 <= args.ack_delay <= 120:
        parser.error("--ack-delay 必須介於 0 到 120")

    queue_name = QUEUES[args.service]

    print(f"測試服務：{args.service}")
    print(f"使用 Queue：{queue_name}")
    print("本程式不會扣庫存、付款或發出實際通知。")

    consume_events(
        queue_name,
        handle_sample_event,
        ack_delay=args.ack_delay,
        once=args.once,
    )


if __name__ == "__main__":
    main()