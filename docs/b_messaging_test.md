
# RabbitMQ 事件傳遞測試紀錄

## 一、測試環境

- 作業系統：Windows 11
- 執行環境：Docker Desktop
- RabbitMQ：4.4.1-management
- Python：Python 3
- AMQP Port：5672
- Management UI：15672
- Python 套件：Pika、python-dotenv

## 二、RabbitMQ 架構

### Exchange

| Name | Type | Durable |
|---|---|---|
| ecommerce.events | topic | true |
| ecommerce.dlx | direct | true |

### Queue

| Queue | Binding Key |
|---|---|
| inventory.order-created | order.created |
| payment.order-created | order.created |
| notification.order-created | order.created |

另外建立三個對應的 DLQ。

## 三、功能測試

### Test 01：事件發布與分發

- 發布一筆 OrderCreated 事件。
- Routing Key：order.created。
- 確認三個服務 Queue 各收到一份訊息。

結果：通過。

### Test 02：Manual ACK

- Consumer 接收事件。
- 暫緩 ACK 30 秒。
- 確認 Ready 變成 0、Unacked 變成 1。
- 完成處理後送出 ACK。

結果：通過。

### Test 03：多服務事件接收

- Inventory、Payment、Notification 分別接收事件。
- 比對三個 Consumer 的 event_id。

結果：三個服務取得相同 event_id，通過。

### Test 04：Consumer 中斷與重新投遞

- Consumer 取得訊息但不 ACK。
- 關閉 Consumer 連線。
- 確認訊息重新進入原 Queue。
- 重新啟動 Consumer。
- 確認 redelivered = True。

結果：通過。

### Test 05：DLQ 錯誤處理

- 發布缺少 order_id 的錯誤事件。
- Consumer 執行資料驗證。
- 發現錯誤後執行 basic_nack(requeue=False)。
- 確認訊息進入 inventory.order-created.dlq。

結果：通過。

## 四、測試結論

本次完成 RabbitMQ 環境建置及事件傳遞功能。

成功建立 Topic Exchange、三個服務 Queue 與對應的死信 Queue。

透過 Python 與 Pika 實作事件發布、訊息接收及手動 ACK，並驗證同一事件能分別傳遞給 Inventory、Payment 與 Notification。

此外，透過 Consumer 中斷及錯誤事件測試，驗證 RabbitMQ 的訊息重新投遞與 Dead Letter Queue 機制。

目前已完成訊息傳遞基礎，後續將與訂單、庫存、付款及通知模組整合。

## 五、目前尚未涵蓋

- 自動重試及 Retry Queue。
- 正式業務邏輯與資料庫持久化。
- event_id 冪等性去重。
- Analytics Consumer 擴充。
- 多服務整合測試。
