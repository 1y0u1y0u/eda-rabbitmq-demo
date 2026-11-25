import os
from pathlib import Path

from dotenv import load_dotenv


# 找到專案根目錄，再讀取根目錄中的 .env。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def required_env(name):
    """取得必要環境變數；缺少時顯示明確錯誤。"""
    value = os.getenv(name)

    if not value:
        raise ValueError(f"請在 .env 設定 {name}")

    return value


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")


# 正常訂單事件的 Exchange 與 Routing Key。
EXCHANGE_NAME = "ecommerce.events"
EXCHANGE_TYPE = "topic"
ROUTING_KEY = "order.created"


# 每個服務使用自己的 Queue。
QUEUES = {
    "inventory": "inventory.order-created",
    "payment": "payment.order-created",
    "notification": "notification.order-created",
}


# 死信 Exchange，處理後續被拒絕且不重新入列的訊息。
DEAD_LETTER_EXCHANGE = "ecommerce.dlx"