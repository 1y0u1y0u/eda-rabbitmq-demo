import json
import pika

from common.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_VHOST,
    EXCHANGE_NAME,
    EXCHANGE_TYPE,
    ROUTING_KEY,
    QUEUES,
    DEAD_LETTER_EXCHANGE,
)


def get_connection():
    """使用 .env 中的設定連接 RabbitMQ。"""
    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=30,
        connection_attempts=3,
        retry_delay=2,
        socket_timeout=10,
    )

    return pika.BlockingConnection(parameters)


def declare_topology():
    """建立本專題使用的 Exchange、Queue 與 Binding。"""
    connection = get_connection()

    try:
        channel = connection.channel()

        # 1. 正常訂單事件使用的 Exchange。
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE,
            durable=True,
        )

        # 2. 死信使用的 Exchange。
        channel.exchange_declare(
            exchange=DEAD_LETTER_EXCHANGE,
            exchange_type="direct",
            durable=True,
        )

        for queue_name in QUEUES.values():
            dead_letter_queue = f"{queue_name}.dlq"

            # 3. 先建立該服務的死信 Queue。
            channel.queue_declare(
                queue=dead_letter_queue,
                durable=True,
                exclusive=False,
                auto_delete=False,
                arguments={
                    "x-queue-type": "classic",
                },
            )

            # 每個服務的死信依原 Queue 名稱分流。
            channel.queue_bind(
                exchange=DEAD_LETTER_EXCHANGE,
                queue=dead_letter_queue,
                routing_key=queue_name,
            )

            # 4. 建立正常事件 Queue，指定死信去向。
            channel.queue_declare(
                queue=queue_name,
                durable=True,
                exclusive=False,
                auto_delete=False,
                arguments={
                    "x-queue-type": "classic",
                    "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
                    "x-dead-letter-routing-key": queue_name,
                },
            )

            # 5. 訂閱 order.created 事件。
            channel.queue_bind(
                exchange=EXCHANGE_NAME,
                queue=queue_name,
                routing_key=ROUTING_KEY,
            )

    finally:
        if connection.is_open:
            connection.close()

def publish_event(event):
    """發布一筆 OrderCreated 事件，等待 RabbitMQ 確認。"""

    # 這裡只檢查傳遞層必要欄位。
    # 完整訂單資料驗證之後由共用事件驗證模組負責。
    if not isinstance(event, dict):
        raise ValueError("event 必須是 Python dict")

    if not isinstance(event.get("event_id"), str):
        raise ValueError("event_id 必須是字串")

    if not event["event_id"].strip():
        raise ValueError("event_id 不可空白")

    if event.get("event_type") != "OrderCreated":
        raise ValueError("目前只支援 OrderCreated 事件")

    # 先轉成 JSON，再編碼為 UTF-8 位元組。
    body = json.dumps(
        event,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    connection = get_connection()

    try:
        channel = connection.channel()

        # 啟用發布確認，等待 RabbitMQ 接受訊息。
        channel.confirm_delivery()

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                content_encoding="utf-8",
                delivery_mode=2,
                message_id=event["event_id"],
                type=event["event_type"],
            ),
            mandatory=True,
        )

    finally:
        if connection.is_open:
            connection.close()

def consume_events(
    queue_name,
    handler,
    *,
    ack_delay=0,
    once=False,
):
    """
    接收指定 Queue 的事件。

    handler(event)：由呼叫端提供的處理函式。
    ack_delay：測試用，處理完成後延遲幾秒才 ACK。
    once：True 時接收並處置一份訊息後結束。
    """
    if queue_name not in QUEUES.values():
        raise ValueError(f"不支援的主 Queue：{queue_name}")

    if not 0 <= ack_delay <= 120:
        raise ValueError("ack_delay 必須介於 0 到 120 秒")

    connection = get_connection()

    try:
        channel = connection.channel()

        # 檢查 Queue 已存在，不修改原有設定。
        channel.queue_declare(
            queue=queue_name,
            passive=True,
        )

        # 同一時間最多保留一份尚未確認的訊息。
        channel.basic_qos(prefetch_count=1)

        def on_message(ch, method, properties, body):
            print()
            print(f"[RECEIVED] Queue：{queue_name}")
            print(f"重新投遞：{method.redelivered}")

            try:
                event = json.loads(body.decode("utf-8"))

                if not isinstance(event, dict):
                    raise ValueError("事件 JSON 必須是物件")

                # 業務或測試處理由呼叫端提供。
                handler(event)

            except Exception as exc:
                print(
                    f"[ERROR] {type(exc).__name__}: {exc}"
                )

                # 技術處理失敗：拒絕且不重新入列。
                # Broker 依先前的 DLX 設定處理死信路由。
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=False,
                )

                print("[NACK] 已送出拒絕，請檢查對應 DLQ。")

            else:
                if ack_delay > 0:
                    print(
                        f"[WAIT] 已完成測試處理，"
                        f"{ack_delay} 秒後送出 ACK。"
                    )
                    print("現在可到管理頁觀察 Unacked。")

                    # 等待時仍處理 RabbitMQ 連線事件。
                    connection.sleep(ack_delay)

                # ACK 放在處理成功之後。
                ch.basic_ack(
                    delivery_tag=method.delivery_tag,
                )

                print(
                    f"[ACK SENT] event_id："
                    f"{event.get('event_id')}"
                )

            if once:
                ch.stop_consuming()

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=False,
        )

        print(f"正在等待 Queue：{queue_name}")
        print("按 Ctrl+C 可停止接收。")

        channel.start_consuming()

    except KeyboardInterrupt:
        print("\n正在停止接收並關閉連線……")

    finally:
        if connection.is_open:
            connection.close()