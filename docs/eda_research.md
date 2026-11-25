
# Event-Driven Architecture (EDA) 研究

## 1. 研究背景與動機

現代軟體系統通常由多個功能模組組成，不同模組需要互相交換資料，以完成完整的業務流程。

以電商訂單系統為例，當使用者建立訂單後，系統通常需要執行庫存更新、付款處理及訂單通知等工作。

在傳統的直接呼叫架構中，訂單服務需要直接呼叫其他服務，並等待對方回傳處理結果。當系統功能逐漸增加時，模組之間的依賴關係也可能變得複雜，增加系統維護及擴充的難度。

因此，本組選擇研究事件驅動架構（Event-Driven Architecture, EDA），探討如何透過事件發布與訂閱機制，降低模組之間的直接依賴，並以 RabbitMQ 實作電商訂單管理系統，觀察事件驅動架構在實際系統中的運作方式。

## 2. 傳統同步呼叫架構

傳統同步呼叫（Synchronous Communication）是指一個服務直接呼叫另一個服務，並等待對方完成工作及回傳結果後，才繼續執行後續流程。

以本組的電商訂單系統為例，使用者建立訂單後，Order Service 會依序呼叫以下服務：

1. Inventory Service：更新商品庫存。
2. Payment Service：處理付款。
3. Notification Service：產生訂單通知。

這種方式讓呼叫端可以直接取得其他服務的處理結果，但也會使服務之間產生直接依賴。

## 3. 傳統架構的模組依賴問題

### 3.1 呼叫介面依賴（Interface Dependency）

在傳統直接呼叫架構中，Order Service 必須知道其他服務的呼叫方式、函式名稱、參數及回傳格式。

例如，Order Service 需要直接呼叫 Inventory Service 的 update_stock() 函式。

如果 Inventory Service 修改函式名稱、參數或介面，Order Service 可能也需要跟著修改，增加程式維護成本。

### 3.2 時間與可用性依賴（Temporal and Availability Dependency）

傳統同步呼叫需要等待被呼叫的服務回傳結果。

如果某個服務處理速度較慢，或暫時無法使用，呼叫端可能需要等待、逾時或進行錯誤處理。

因此，訂單服務的執行流程可能受到其他服務的可用性及回應時間影響。

### 3.3 功能擴充依賴（Extension Dependency）

當系統新增功能時，例如新增 Analytics Service 負責統計訂單資料，傳統直接呼叫架構可能需要修改 Order Service，加入新的服務呼叫。

當系統功能越來越多，Order Service 就可能需要依賴越來越多的服務，使原本的程式碼變得複雜，也增加後續維護及修改的風險。


## 4. EDA 如何改善傳統架構的模組依賴問題

事件驅動架構（Event-Driven Architecture, EDA）透過事件發布與訂閱機制，改變模組之間的溝通方式。

在本組的電商系統中，Order Service 不再直接呼叫 Inventory Service、Payment Service 及 Notification Service，而是將 OrderCreated 事件發布至 RabbitMQ，再由各個 Consumer 獨立接收並處理。

### 4.1 降低呼叫介面依賴

傳統架構中，Order Service 必須知道各服務的呼叫介面、參數及回傳格式。

EDA 中，Order Service 只需要依照共同事件格式發布 OrderCreated 事件，不需要知道 Consumer 的內部實作及呼叫函式。

因此，即使 Consumer 的內部程式有所調整，只要仍能正確處理既有事件格式，通常不需要修改 Order Service。

### 4.2 降低時間與可用性依賴

傳統同步呼叫中，Order Service 需要等待其他服務完成處理。

EDA 則將事件發布與 Consumer 的業務處理分開進行。

例如 Notification Service 暫時停止時，只要 RabbitMQ 正常運作，且訊息佇列及持久化設定正確，訂單事件仍可保留在 Notification Queue 中，等待服務恢復後再處理。

因此，Notification Service 暫時無法使用，不一定會阻止其他 Consumer 繼續處理事件。

### 4.3 降低功能擴充依賴

傳統直接呼叫架構中，如果新增 Analytics Service，可能需要修改 Order Service，加入新的服務呼叫。

EDA 中，只需要新增 Analytics Consumer，並建立對應 Queue 及 Binding，即可訂閱既有的 OrderCreated 事件。

原本的 Order Service 不需要修改事件發布邏輯。

這使系統新增功能時，可以降低對原有模組的修改需求。

### 4.4 EDA 仍然存在的依賴

EDA 並不是完全沒有模組依賴。

Producer 與 Consumer 仍然必須遵守共同的事件資料格式，例如 event_id、event_type、order_id 等欄位。

此外，系統也依賴 RabbitMQ 提供正常的訊息傳遞功能。

因此，EDA 主要改善的是模組之間的直接呼叫依賴，而不是消除所有依賴關係。

## 5. 傳統同步呼叫與 EDA 比較

| 比較項目 | 傳統同步呼叫 | EDA |
|---|---|---|
| 模組溝通方式 | 直接呼叫其他服務 | 透過事件發布與訂閱 |
| 介面依賴 | 呼叫端需要知道服務介面 | 主要依賴共同事件格式 |
| 執行方式 | 呼叫端等待回應 | Consumer 可非同步處理 |
| 服務暫停 | 可能造成呼叫逾時或失敗 | 可透過 Queue 暫存待處理事件 |
| 功能擴充 | 可能需要修改原有呼叫流程 | 可新增 Consumer 訂閱事件 |
| 除錯難度 | 呼叫流程通常較容易追蹤 | 跨服務事件追蹤較複雜 |
| 資料一致性 | 可直接取得同步處理結果 | 需考慮最終一致性 |

以上比較以本組設計的直接同步呼叫案例與 RabbitMQ 事件驅動案例為基礎，並不代表所有非 EDA 系統都具有相同限制。
