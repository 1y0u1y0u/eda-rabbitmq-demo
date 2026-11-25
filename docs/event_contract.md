# OrderCreated 事件與模組介面契約

更新日期：2026-11-25。共同維護：B／C；C 的訂單回傳介面需 E 配合，Consumer 與紀錄格式需 D／E 配合。

**狀態：第一版協作契約草案。**既有事件核心格式與 B 已實作的傳遞介面依現有規格沿用；第 4 節細部驗證提案、第 6 節訂單回傳提案、第 8 節初始商品與第 10 節確認清單尚待相關組員確認，不得當成 C 已同意或程式已完成。

## 1. 核對範圍與責任

核對儲存庫提交：[`6ab20e977d07daeaf4a6274754ccb9c919e55333`](https://github.com/1y0u1y0u/eda-rabbitmq-demo/commit/6ab20e977d07daeaf4a6274754ccb9c919e55333)。搭配 [project_spec.docx](project_spec.docx)、[team_handoff.md](team_handoff.md)、[rabbitmq_setup.md](rabbitmq_setup.md)。

| 項目 | 現況與責任 |
|---|---|
| common/config.py、common/messaging.py | B 已實作；名稱、參數及目前行為見第 2、5 節 |
| scripts/publish_sample.py | 已提供 OrderCreated 範例；不是正式訂單建立服務 |
| services/__init__.py | 已存在，不需重建 |
| common/event_schema.py、schemas/order_created.example.json | C 主責新增，B 核對傳遞端相容性；核對提交中尚未存在 |
| services/order_service.py、services/inventory_service.py、data/products.json | C 主責；核對提交中尚未存在 |
| services/payment_service.py、services/notification_service.py | D 主責；核對提交中尚未存在 |
| services/analytics_service.py | E 第二階段規劃，須確認承接，B 先擴充拓樸 |

本文件補足開發依據，未修改程式，也未重新執行整合測試。原分工與正式檔名不變；規格與程式不一致時應列出差異，不把規劃誤稱已實作。

## 2. 傳遞命名與路由

| 設定 | 第一版值 |
|---|---|
| event_type | OrderCreated |
| event_version | 1 |
| 發布 Exchange／type | ecommerce.events／topic |
| 發布 routing key | order.created |
| producer | order_service |
| 死信 Exchange／type | ecommerce.dlx／direct |
| 訊息格式 | UTF-8 JSON object |
| 持久化 | Exchange、Queue durable；訊息 delivery_mode=2 |
| 接收方式 | manual ACK、prefetch_count=1 |

| 服務 | 主 Queue | DLQ |
|---|---|---|
| Inventory | inventory.order-created | inventory.order-created.dlq |
| Payment | payment.order-created | payment.order-created.dlq |
| Notification | notification.order-created | notification.order-created.dlq |

三個主 Queue 都以 order.created 綁定；同一事件各有一份，各服務獨立處理。同一 Queue 內的多個 Consumer 會競爭訊息，不是每個都收到一份。各主 Queue 的死信 routing key 為該主 Queue 名稱，路由到自己的 DLQ。

Analytics 的 analytics.order-created 尚未加入目前 QUEUES 名單；需 B 新增 Queue、Binding、DLQ 與設定後才接入。新綁定只接收之後路由進來的事件，不自動補收歷史事件。

## 3. 第一版事件核心格式

以下是可解析的有效範例；固定 ID 僅供文件展示，不可每筆新訂單重複使用。

```json
{
  "event_id": "EVT-4d0e45850fd3446483ce78b887ca7d06",
  "event_type": "OrderCreated",
  "event_version": 1,
  "occurred_at": "2026-11-25T14:00:00+08:00",
  "producer": "order_service",
  "correlation_id": "ORD-3d8d2b9d9985474f80d74920c3dfc275",
  "data": {
    "order_id": "ORD-3d8d2b9d9985474f80d74920c3dfc275",
    "product_id": "P001",
    "quantity": 2,
    "unit_price": "500.00",
    "total_amount": "1000.00",
    "currency": "TWD"
  }
}
```

| 欄位 | JSON 型態 | 核心約定 |
|---|---|---|
| event_id | string | 非空白、每個新事件唯一；重送同一事件保留原值 |
| event_type | string | 固定 OrderCreated |
| event_version | integer | 第一版為 1 |
| occurred_at | string | ISO 8601、含時區，表示事件建立時間 |
| producer | string | 正式發布者為 order_service |
| correlation_id | string | 第一版串聯同一訂單，沿用 sample 的 order_id 值 |
| data | object | 訂單資料容器 |
| data.order_id | string | 非空白訂單識別碼 |
| data.product_id | string | 非空白商品識別碼 |
| data.quantity | integer | 大於 0 |
| data.unit_price | string | 非負十進位金額字串 |
| data.total_amount | string | 十進位金額字串，等於單價乘數量 |
| data.currency | string | 第一版沿用 TWD |

第一版是一筆事件含一項商品及數量，未規劃購物車 items 陣列、付款完成事件或跨服務交易流程。C 若需擴充，先與 B、D、E 協調，不在自己的分支直接改掉全組依賴的格式。

現有 sample 的 ID 採 ORD-/EVT- 加 uuid4().hex；建議正式服務沿用，但不要把前綴或固定字數當成既有傳遞層已強制驗證的條件。重送應保留原 event_id、order_id、occurred_at 及原業務資料；修正內容的事件如何重送需另行協調，不能偷偷改內容卻沿用已處理的 ID。

## 4. C 的驗證模組

### 4.1 沿用的介面規劃

```python
validate_order_created(event)
```

位置：common/event_schema.py。有效事件正常回傳 None；無效事件拋出 ValueError，訊息指出欄位路徑與原因，例如 `data.quantity must be a positive integer`。不得用回傳 False 代表驗證失敗，否則 Consumer 外層會當作正常完成並 ACK。

此函式為 C 待實作介面，並非目前已存在。建議作為純資料驗證：不連 RabbitMQ、不扣庫存、不付款、不查可變動的庫存餘額，也不默默修改原事件。

正式發布前由 C 呼叫；正式 Consumer 在 handler 中呼叫相同驗證函式，再進行業務。B 的共用 consume_events 只解析 JSON object，不自動執行完整 schema 驗證。

### 4.2 細部規則提案，待 C／B 確認

核心型態與必要欄位沿用第 3 節；以下補足容易讓不同 AI 寫出不同結果的細節，確認後再固定驗收：

| 細節 | 建議採用的第一版規則 |
|---|---|
| 整數判斷 | quantity 與 event_version 不接受 bool；quantity 不接受字串 "2" 或 2.0 |
| 必要字串 | 空字串、全空白拒絕；ID 不含頭尾空白，不靜默修剪後當成同一 ID |
| 金額輸出 | 固定非負、兩位小數，不接受科學記號、NaN、Infinity、逗號或貨幣符號；例如 "500.00" |
| 金額計算 | 以 Decimal 計算和比對 total_amount，不先轉 float；超過兩位小數的輸入先拒絕，不自行決定四捨五入 |
| 時間 | 可解析且有時區；sample 用 +08:00。可接受其他明確時區，不因顯示時區不同拒絕有效時間 |
| 版本 | 不支援的 event_version 拒絕；v1 不自動猜測 v2 格式 |
| producer／currency | 正式 v1 固定 order_service／TWD；DLQ 注入工具的 dlq_test 不屬正常事件 |
| correlation_id | v1 等於 data.order_id；若將來要跨多事件追蹤，再討論擴充 |
| 額外欄位 | 建議保留並忽略未知欄位，但必填欄位與既有語意不可改；不得讓額外欄位啟動未約定業務 |

這些規則不是全部都已由 B 程式保證。schemas/order_created.example.json 由 C 按確認後規則建立，至少包含可與現有 sample 相容的 P001 範例。

## 5. B 已實作的共用傳遞介面

### 5.1 初始化與連線

`declare_topology()` 建立第 2 節的 Exchange、Queue、Binding 與 DLQ；一般由 `python -m scripts.setup_rabbitmq` 呼叫。`publish_event` 不自行宣告拓樸；`consume_events` 只被動檢查指定 Queue 存在。先 setup，再發布及接收。

`get_connection()` 讀取 .env。現有設定為 heartbeat=60、blocked_connection_timeout=30、connection_attempts=3、retry_delay=2、socket_timeout=10。這不是執行中自動重連或自動業務重試。

### 5.2 publish_event(event)

```python
from common.messaging import publish_event

publish_event(event)
```

目前實作會：

1. 檢查 event 是 dict、event_id 是非空白字串、event_type 等於 OrderCreated。
2. 使用 json.dumps(..., ensure_ascii=False, allow_nan=False) 編碼 UTF-8 JSON；不可序列化資料會失敗。
3. 啟用 Publisher Confirm，以 mandatory=True 發布到指定 Exchange／routing key。
4. 設定 content_type=application/json、content_encoding=utf-8、delivery_mode=2、message_id=event_id、type=event_type。
5. 正常完成回傳 None；錯誤以例外傳出。不要寫 `if publish_event(event)` 判定成功。

AMQP correlation_id property 目前未設定；請從 JSON 本體的 correlation_id 讀取。完整欄位驗證、ID 產生、金額計算、訂單結果保存與重送控制仍由 C 實作。

正常返回表示這次 Broker 確認且未回報無法路由，不表示每個預期 Queue 均存在，也不表示 Consumer／付款已完成。連線在確認回來前中斷時，可能已送達但發布端不知道；例外不能一律解讀為「完全沒有送出」。現有 finally 中關閉連線的錯誤也可能在已送出後傳出，因此結果不明應保守處理。

### 5.3 consume_events(queue_name, handler, *, ack_delay=0, once=False)

```python
from common.config import QUEUES
from common.messaging import consume_events

# 各服務在自己的模組中提供 handle_event。
consume_events(QUEUES["inventory"], handle_event)
```

queue_name 必須是 QUEUES 中的主 Queue 值，不是 "inventory" 短名稱，也不接受 DLQ 名稱。ack_delay 為測試參數，範圍 0～120 秒；once=True 在處置一筆後結束，包含 ACK 或 NACK，不是無訊息時立即退出。

| handler 或解析結果 | 共用外層行為 | 業務端責任 |
|---|---|---|
| 成功正常返回 | ACK | 先保存業務結果及去重狀態 |
| 重複事件，正常返回 | ACK | 確認本服務已完成，不再重複副作用 |
| 庫存不足／模擬付款拒絕，保存結果後返回 | ACK | 可預期業務結果不是重試同一筆就會修好的技術錯誤 |
| 解析或 handler 拋 Exception | NACK，requeue=False | 記錄原因，由既有 DLX 路由到對應 DLQ |
| 斷線或程序結束時仍未 ACK | Broker 在連線關閉後可重新投遞 | 業務端應能處理重複投遞 |

**return False 也會 ACK。**handler 不自行 ACK／NACK，不需要拿到 Pika channel。若技術失敗被 handler 捕捉，應記錄後重新拋出，不可吞掉例外正常返回。Broker／連線失效時 ACK／NACK 本身可能未送達，不能因本機業務執行過就推論 Broker 已收到確認。

目前使用 classic Queue 的 DLX 設定，不宣稱所有故障條件下死信轉送都絕不遺失；需在既定測試環境核對 DLQ 實際內容。

## 6. C 對 E 的訂單建立介面提案

### 6.1 函式名稱維持原規劃

```python
create_order(product_id, quantity, unit_price)
```

位置：services/order_service.py。C 建立訂單與事件，呼叫 validate_order_created，再呼叫 publish_event；不直接呼叫庫存、付款、通知 handler。

**以下是供 C／E 確認的具體提案，不是已實作介面：**product_id 用 str、quantity 用 int（排除 bool）、unit_price 用十進位 str 或 Decimal，避免二進位 float。單價來源與是否允許使用者輸入，依第 8 節協調。

### 6.2 回傳結構提案

輸入無效時先拋 ValueError，不發布；E 顯示欄位錯誤。通過驗證並建立識別碼後，建議回傳下列 dict，統一由 publish_status 表示「發布狀態」：

```json
{
  "order_id": "ORD-3d8d2b9d9985474f80d74920c3dfc275",
  "event_id": "EVT-4d0e45850fd3446483ce78b887ca7d06",
  "publish_status": "confirmed",
  "message": "事件發布已確認，後續處理中"
}
```

| publish_status 提案 | 使用條件 | E 顯示意義 |
|---|---|---|
| confirmed | publish_event 正常返回 | Broker 已確認；不等於庫存、付款或通知成功 |
| not_published | C／B 能證明本次沒有送出或無任何路由投遞 | 尚未發布，不表示訂單已完成 |
| unknown | 送出／確認過程中斷或其他無法證明投遞結果的例外 | 發布結果不明，需要查核，不能提示直接重新下單 |

C 應提出實際例外分類給 B 核對；不能只用 `except Exception: not_published`。若目前無法可靠辨識階段，對無法判定的例外採 unknown，而不是猜測失敗。message 不放連線密碼、完整敏感設定或原始追蹤堆疊。

是否採用上述 dict、錯誤例外方式及狀態拼字，須 C／E 確認後才成為正式契約；若已有實作，先比對，不直接覆寫。

### 6.3 發布與重送的邊界

同一事件重送必須保留原事件資料與識別碼。現有 create_order 規劃只有三個業務參數，不能透過再次呼叫它建立新 ID，再宣稱這是安全重送。

C 需與 B／E 確認如何在 runtime/ 保存待發布事件及狀態、如何找到原事件再重送；可先採人工控制的測試流程，不新增未約定的自動重試。E 在 confirmed／unknown 後不可無提示地自動重複送單。若使用者確實建立另一筆新訂單，才產生新的 order_id 與 event_id。

保存事件與 Broker 發布不是同一個交易，本版未實作 transactional outbox 或端到端 exactly-once，不宣稱上述提案已消除所有失敗窗口。

## 7. Consumer 業務、去重與紀錄

- Inventory、Payment、Notification 各自驗證並保存 event_id 的處理狀態。不能全組共用一個「已處理」旗標，否則一個服務做完會讓其他服務跳過。
- 建議使用 SQLite，將本服務狀態更新與完成標記放在同一個交易，提交成功才返回。若多個相同服務實例共用資料庫，需有唯一鍵／交易保護，不能只做查詢再寫入而沒有競爭控制。
- 重複事件只跳過已確認完成的本服務結果；不能先標記成功、再扣庫存或寫業務資料。
- 可預期庫存不足或模擬付款拒絕，保存該次結果及去重狀態後 ACK。相同事件重送不得在之後庫存補足時悄悄重新變成成功，除非另行定義新的業務操作。
- 技術例外或格式錯誤拋出，由外層送 DLQ；未完成的交易需回滾。沒有目前的自動業務重試流程。
- JSONL 可作展示紀錄，但單獨寫 JSONL 並不等於業務更新與去重的原子交易。實際檔案、schema、重啟續接與重置方式由各業務主責記錄。
- Notification 只記錄「訂單已建立」，不得收到 OrderCreated 就宣稱付款成功。庫存與付款無保證先後，且沒有跨服務回滾／補償。

D 主責 docs/event_processing_log.md；C／E 配合。建議共用紀錄至少含 service、event_id、order_id、處理時間（含時區）、業務狀態、原因／錯誤類別。精確欄位與狀態字串由 D 與 C／E 確認，不在本草案代為定案。執行狀態放 runtime/；可提交去識別的說明範例，實際資料庫與執行紀錄不提交。

## 8. 初始商品與庫存提案，待 C 確認

C 維護 data/products.json，作為可版本控制的種子資料；本文件不新增或替 C 實作這個檔案。

建議第一個可重現案例：商品 P001、單價 "500.00"、初始庫存 10、數量 2，首次成功後庫存為 8；同一事件重送後仍為 8。**庫存 10 是本文件提案，不是目前已有資料。**具體 JSON 結構、商品名稱與其他商品由 C 決定後寫回此節。

C 需明確定義：

1. products.json 欄位與商品 ID；至少支援現有 sample 的 P001。
2. 單價來自商品資料還是允許輸入；建議由商品資料決定，若保留 unit_price 參數則核對與商品價一致，避免介面輸入任意金額。
3. 查無商品的處理位置與狀態。建議正式 create_order 發布前拒絕未知商品；若 Consumer 收到格式有效但未知的商品，與 D／E 協調業務失敗紀錄方式，不自行當成重試條件。
4. 初始庫存何時載入、服務重啟是否保留目前庫存；不能每次啟動都覆寫成初始值。
5. 測試重置如何同時處理業務狀態、去重紀錄與 Queue 中舊訊息；在停止服務、確認資料用途後才重置，不在一般啟動流程清空資料。

庫存可用性由 Inventory 判斷並記錄；事件 schema 驗證器只驗資料形狀與數值，不因當下庫存不足而改變事件是否合法。

## 9. C 實作後的整合驗收

以下為待執行清單，沒有預填「通過」。C 先提供函式、入口及初始化方式，B 驗證傳遞相容性，D／E 配合業務紀錄及整合。

| 測試 | 應驗證的結果 |
|---|---|
| 現有 sample 相容性 | validate_order_created 接受 build_sample_event() 產生的有效事件；金額與時間規則一致 |
| 無效輸入 | quantity=0／負數、缺少必要欄位被拒絕；若採細則，bool、浮點數量、非法金額／時區也被拒絕 |
| 金額一致性 | Decimal 計算正確；total_amount 與單價乘數量不符時拒絕 |
| 正常建立訂單 | 同一事件送到三個服務；發布回傳 confirmed 只表示發布狀態 |
| 發布異常 | 模擬無法路由／連線失效等情況；確認不把所有例外標成 not_published，也不產生新的 ID 自動重送 |
| 庫存與去重 | 按確認的初始資料扣一次；原事件重送、服務重啟後仍不重複扣除 |
| 業務失敗 | 庫存不足或模擬付款拒絕保存結果並 ACK，不無限重排 |
| 技術失敗 | handler 拋錯進對應 DLQ，未完成業務交易不留下成功標記 |
| 處理後未 ACK 中斷 | 已提交的業務在重投遞時不再執行；需實際測試，不能僅以 sample 中斷測試替代 |
| 通知暫停與恢復 | 其他服務處理同一事件，通知 Queue 保留；恢復後記錄訂單建立通知 |

測試證據記錄提交、event_id、原始狀態、實際結果。依教師要求，說明事件契約本身仍是一種依賴；EDA 降低直接呼叫及時間耦合，不等於完全無依賴。

## 10. 需要 C 確認的清單

以下預設均為「待確認」，PR 開立或合併不代表內容已由 C 同意。由 C 在 PR 留言逐項回覆，B 整理進本節；涉及 E／D 的項目一併確認。

| 編號 | 確認事項 | 需參與者 | 目前狀態 |
|---|---|---|---|
| C1 | 沿用 v1 欄位、ID／時間／金額格式、驗證成功 None／失敗 ValueError，以及第 4 節細則 | C、B；D／E 知悉 | 待確認 |
| C2 | create_order 的輸入型態、回傳 dict、publish_status 三種狀態及輸入錯誤處理 | C、E、B | 待確認 |
| C3 | 單價來源、products.json 結構、P001 初始庫存與未知商品處置 | C、E | 待確認 |
| C4 | 待發布事件保存、發布結果不明的處理與原 event_id 重送方式 | C、B、E | 待確認 |
| C5 | Inventory 持久化、去重交易、重啟續接、庫存不足 ACK 與測試重置方式 | C、B；D／E 對齊 | 待確認 |
| C6 | 各自模組入口、執行方式、共用紀錄欄位與一筆完整整合案例 | C、D、E；B 配合 | 待確認 |

確認後在本節記錄決議、日期與對應 PR／提交；有變動同步更新 project_spec.docx、team_handoff.md 與相關實作。未確認部分可先作協作草案上傳供討論，但不要宣稱已完成正式介面驗收。

## 11. 來源與維護

- [目前共用設定](../common/config.py)、[傳遞介面](../common/messaging.py)、[有效 sample](../scripts/publish_sample.py)、[sample Consumer](../scripts/consume_sample.py)。
- [RabbitMQ ACK 與 Publisher Confirm](https://www.rabbitmq.com/docs/confirms)。
- [RabbitMQ Dead Letter Exchanges](https://www.rabbitmq.com/docs/dlx)。

來源說明機制；本專案確切行為以第 1 節提交的程式及共同決議為準。保留實作限制與待確認狀態，不以文件描述替代可執行程式。
