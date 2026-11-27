
from services.order_service import create_order


def main():

    print("===== Order Service 測試 =====")

    try:
        result = create_order(
            product_id="P001",
            quantity=2,
            unit_price="500.00"
        )

        print("\n===== 訂單建立結果 =====")
        print("Order ID:", result["order_id"])
        print("Event ID:", result["event_id"])
        print("Publish Status:", result["publish_status"])

        if result.get("error"):
            print("Error:", result["error"])

    except ValueError as error:
        print("[VALIDATION ERROR]", error)


if __name__ == "__main__":
    main()
