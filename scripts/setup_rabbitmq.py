from common.config import (
    EXCHANGE_NAME,
    EXCHANGE_TYPE,
    ROUTING_KEY,
    QUEUES,
    DEAD_LETTER_EXCHANGE,
)
from common.messaging import declare_topology


def main():
    print("正在連線並建立 RabbitMQ 訊息傳遞結構……")

    declare_topology()

    print()
    print("RabbitMQ 初始化完成")
    print(f"事件 Exchange：{EXCHANGE_NAME}")
    print(f"Exchange 類型：{EXCHANGE_TYPE}")
    print(f"Routing Key：{ROUTING_KEY}")
    print(f"死信 Exchange：{DEAD_LETTER_EXCHANGE}")
    print()

    for service, queue_name in QUEUES.items():
        print(f"[{service}]")
        print(f"  主 Queue：{queue_name}")
        print(f"  死信 Queue：{queue_name}.dlq")

    print()
    print("共完成 2 個自訂 Exchange、3 個主 Queue、3 個死信 Queue。")
    print("請到 RabbitMQ 管理頁面確認。")


if __name__ == "__main__":
    main()