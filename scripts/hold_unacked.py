
import argparse
import json

from common.config import QUEUES
from common.messaging import get_connection


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--service",
        required=True,
        choices=list(QUEUES.keys()),
    )

    args = parser.parse_args()
    queue_name = QUEUES[args.service]

    connection = get_connection()

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue=queue_name,
            passive=True,
        )

        # 取得一筆訊息，但不自動 ACK。
        method, properties, body = channel.basic_get(
            queue=queue_name,
            auto_ack=False,
        )

        if method is None:
            print("Queue 沒有待處理訊息。")
            return

        event = json.loads(body.decode("utf-8"))

        print("=" * 45)
        print("已取得訊息，但尚未 ACK")
        print(f"服務：{args.service}")
        print(f"Queue：{queue_name}")
        print(f"event_id：{event.get('event_id')}")
        print(f"redelivered：{method.redelivered}")
        print("=" * 45)

        print("現在請到 RabbitMQ 管理頁觀察 Unacked。")
        print("按 Ctrl+C 模擬 Consumer 中斷。")

        # 保持連線，但不送 ACK。
        while True:
            connection.sleep(1)

    except KeyboardInterrupt:
        print("\n收到中斷指令。")

    finally:
        if connection.is_open:
            connection.close()

        print("RabbitMQ 連線已關閉。")
        print("未確認訊息應重新進入原 Queue。")


if __name__ == "__main__":
    main()
