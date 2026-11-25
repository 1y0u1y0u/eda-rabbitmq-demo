# A、B、C、D、E 全組操作與整合說明

更新日期：2026-11-25。適用環境：Windows PowerShell。

儲存庫：https://github.com/1y0u1y0u/eda-rabbitmq-demo

本說明已核對目前 main 的 compose.yaml、.env.example、requirements.txt、common/config.py、common/messaging.py 及測試程式。B 已在自己的電腦完成傳遞測試；C、D 仍需在各自電腦驗證環境。本文件不代表正式庫存、付款或通知功能已完成。


## 0. 本版統一事項與目前進度

本文件搭配 `docs/project_spec.docx` 使用，取代舊 `cd_handoff.md`。請勿同時將舊版交接檔當成有效規格。檔名中的 `(1)` 只是下載時的重複檔名後綴，不是正式版本號。

核對基準為 GitHub `main` 的提交 `651998a0bd62f4f06c164f0e388a96cafe24d593`，核對時遠端只有 main。

- 已存在：B 的 common/、scripts/、compose.yaml、.env.example、.gitignore、requirements.txt、訊息流程圖、傳遞測試紀錄及截圖。
- 尚未存在：正式 services/ 業務程式、common/event_schema.py、schemas/、data/products.json、README.md、app.py、Analytics。
- 待補文件：docs/rabbitmq_setup.md、docs/event_contract.md、docs/event_processing_log.md、docs/integration_test.md、docs/demo_script.md，以及 A 的研究與架構圖。
- 不需重命名現有 B 程式。正式 Consumer 檔名統一採用 *_service.py；不要另建 *_consumer.py。
- A 的 system_architecture 圖描述全系統角色與關係；B 的 message_flow 圖描述訊息分發及錯誤處置，兩者用途不同。
- 現有截圖保留原名，b_09 未拍攝，不補造。測試報告只代表已記錄的傳遞情境，不代表正式業務整合已通過。
- `requirements.txt` 目前採版本範圍，尚未完全鎖定實測版本。

### 全組正式檔名與責任

| 人員 | 應交付的主要檔案 |
|---|---|
| A | docs/eda_research.md、docs/system_architecture.mmd、docs/system_architecture.png |
| B | 既有 RabbitMQ 基礎；補 services/__init__.py、docs/rabbitmq_setup.md；與 C 完成 docs/event_contract.md |
| C | common/event_schema.py、schemas/order_created.example.json、services/order_service.py、services/inventory_service.py、data/products.json |
| D | services/payment_service.py、services/notification_service.py、docs/event_processing_log.md |
| E | README.md、docs/integration_test.md、docs/demo_script.md；app.py 為選用介面；第二階段規劃 services/analytics_service.py |

E 統整 report/final_report.docx、report/final_slides.pptx；是否需要 report/demo.mp4 依老師要求。這些是小組規劃的檔名，不是已存在的檔案。

### 規格與程式不一致時

project_spec.docx 規定預定行為；team_handoff.md 規定操作與協作；GitHub 實際檔案表示目前已實作的行為。遇到不一致要列出差異並協調，不能把現有程式的缺漏當成需求已取消，也不能把規劃當成已實作。後續改動需同步維護兩份文件及 docs/event_contract.md。

### A 與 E 如何開始

A 可先閱讀程式、B 的流程圖與測試紀錄，完成 EDA、同步呼叫比較及全系統架構研究；不用為了寫研究強制先安裝 Docker。研究引用可靠來源，明確區分已實作與規劃功能，勿宣稱 EDA 必然更快或永不丟訊息。

E 先依第 2～6 節跑通本機測試，再整理 README、展示腳本及整合測試計畫。C 尚未完成時，可先做介面輸入與畫面草稿，但清楚標示模擬資料；不要宣稱已接上正式訂單服務。第二階段 Analytics 先與 B 約定新增拓樸，再發布新事件驗證擴充。

### 開發前仍要確認的三個細節

1. C 與 E：create_order 的具體回傳結構及例外／結果不明呈現方式。先約定，再實作介面。
2. C：初始庫存資料結構、P001 初始數量與測試重置方式。
3. D：付款成功／拒絕／技術例外如何穩定重現，以及共用紀錄欄位。

兩份文件與程式足以開始各自工作，但不保證不同 AI 產出的模組能直接拼接；必須有上述契約及實際整合驗收。

## 1. 接受邀請與分工

先登入自己的 GitHub 帳號，接受 B 發出的 collaborator 邀請。儲存庫目前為 Public：任何人可讀取，但組員要推送分支，仍需取得協作者權限。

| 人員 | 負責內容 | 建議分支 |
|---|---|---|
| A | EDA 研究與全系統架構圖 | docs/research-a |
| E | 整合、README、展示及第二階段 Analytics（請 E 確認承接） | feature/integration-e |
| B | RabbitMQ 拓樸、共用傳遞層、環境與傳遞測試 | feature/rabbitmq-b |
| C | 事件驗證、訂單建立與發布、庫存處理及去重 | feature/order-inventory-c |
| D | 付款模擬、訂單建立通知、各服務去重 | feature/payment-notification-d |

需要修改 common/config.py、common/messaging.py 或 compose.yaml 時，先與 B 協調；不要各自複製出不同版本。C 可新增 common/event_schema.py。

## 2. 開發前準備

電腦須可使用 Git、Python 3、Docker Desktop（Linux containers）。先啟動 Docker Desktop。

```powershell
git --version
py --version
docker --version
docker compose version
```

任何指令不存在，先完成對應工具安裝。若只有 python 而沒有 py，確認 python --version 是 Python 3，再將下面建立環境的 py 換成 python。

## 3. 下載專案及建立分支

在想存放專案的父資料夾開啟 PowerShell，執行：

```powershell
git clone https://github.com/1y0u1y0u/eda-rabbitmq-demo.git
cd eda-rabbitmq-demo
git status
```

若該資料夾名稱已存在，改在另一個父資料夾 clone，不要覆蓋原有工作。已有正確 clone 的組員不必再 clone；先確認工作目錄乾淨，再執行 git switch main 及 git pull --ff-only origin main，才建立下方分支。

A 只執行：

```powershell
git switch -c docs/research-a
```

E 只執行：

```powershell
git switch -c feature/integration-e
```

C 只執行：

```powershell
git switch -c feature/order-inventory-c
```

D 只執行：

```powershell
git switch -c feature/payment-notification-d
```

同一分支只建立一次；之後回到分支使用 git switch 分支名稱，不加 -c。用 VS Code 的「開啟資料夾」開啟 eda-rabbitmq-demo。以下所有命令都從專案根目錄執行。

## 4. Python 與本機帳密設定

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

下列命令只在第一次、尚未有 .env 時執行，避免覆蓋現有設定：

```powershell
Copy-Item .env.example .env
```

在 VS Code 開啟 .env。保留 host=localhost、port=5672、vhost=/，把 RABBITMQ_PASSWORD 的 CHANGE_ME 換成本機使用的密碼；可保留使用者名稱 eda_user。

每個人使用自己的帳密，不必與 B 相同。Docker 與 Python 都會讀取本機 .env；.env 不提交 GitHub。

本說明直接使用虛擬環境內的 python.exe，因此不需執行 Activate.ps1。

## 5. 啟動 RabbitMQ 與建立拓樸

```powershell
docker compose up -d
docker compose ps
```

等狀態顯示 healthy；如果仍為 starting，稍後再查一次。失敗時先查看：

```powershell
docker compose logs --tail 80 rabbitmq
```

然後執行：

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_rabbitmq
```

預期建立 2 個自訂 Exchange、3 個主 Queue、3 個 DLQ。

瀏覽器開啟 http://localhost:15672 ，使用自己的 .env 帳密登入。

| 主 Queue | 對應 DLQ |
|---|---|
| inventory.order-created | inventory.order-created.dlq |
| payment.order-created | payment.order-created.dlq |
| notification.order-created | notification.order-created.dlq |

重要：目前 compose.yaml 將 5672、15672 綁定在 127.0.0.1。每個人的 localhost 都是自己的電腦；GitHub 只同步程式，不會讓各人的 RabbitMQ 自動互通。開發時各自測試，整合展示時建議將所有服務放在同一台電腦執行。

帳密是在新資料卷初始化時建立；如果 RabbitMQ 曾啟動過，單純修改 .env 不會自動更新舊資料卷中的使用者密碼。遇到登入失敗請交給 B 協助，不要直接刪資料卷。docker compose down -v 會刪除此專案資料卷，不能拿來當一般重新啟動指令。

## 6. 先驗證現有傳遞功能

測試時停止正式 Consumer，也不要同時啟動其他 sample Consumer。第一次全新初始化時，六個 Queue 應為空；若已有訊息，先記錄數量，不要任意清空。

先只發布一次：

```powershell
.\.venv\Scripts\python.exe -m scripts.publish_sample
```

到管理頁確認三個主 Queue 的 Ready 各增加 1。記下 event_id。

再依序執行：

```powershell
.\.venv\Scripts\python.exe -m scripts.consume_sample --service inventory --once
.\.venv\Scripts\python.exe -m scripts.consume_sample --service payment --once
.\.venv\Scripts\python.exe -m scripts.consume_sample --service notification --once
```

驗收：三者收到同一 event_id、均顯示 ACK SENT；若起初全空，最後六個 Queue 應回到 0。

--once 是收到並處置一筆後結束，不是沒有訊息就立刻結束；若一直等待，確認本機主 Queue 中是否有訊息。

此程式只檢查基本欄位並顯示事件，不會扣庫存、執行真實付款或寄送通知。

## 7. 目前共用介面與整合契約

### C：發布事件

```python
from common.messaging import publish_event

# event 為 C 完成欄位驗證後的 Python dict。
publish_event(event)
```

成功正常返回 None，不回傳 True，也不回傳訂單編號。不要寫 if publish_event(event)。訂單編號、事件編號及供介面使用的狀態，由 C 的 create_order() 整理回傳。

publish_event 目前僅檢查 dict、非空 event_id、event_type=OrderCreated，並要求可序列化為 JSON；完整欄位驗證仍需由 C 實作。

發布有使用持久化訊息、Publisher Confirm 與 mandatory。正常返回表示 Broker 確認且未回報無法路由，不等於所有預期 Queue 都存在，也不等於消費者處理完成或付款成功。若連線中斷造成結果不明，重送同一事件要保留 event_id。

事件範例請參考 scripts/publish_sample.py 的 build_sample_event()。第一版欄位包括 event_id、event_type、event_version、occurred_at、producer、correlation_id，以及 data 中的 order_id、product_id、quantity、unit_price、total_amount、currency。金額使用十進位字串；數量為正整數；總額等於單價乘數量。

### C、D：消費事件

目前函式簽名：

```python
consume_events(queue_name, handler, *, ack_delay=0, once=False)
```

各模組定義自己的 handle_event(event) 後，再呼叫以下對應的一行；不要把三個阻塞接收函式連續放在同一個 main 中。

```python
from common.config import QUEUES
from common.messaging import consume_events

# Inventory 模組中：
consume_events(QUEUES["inventory"], handle_event)

# Payment 模組中：
consume_events(QUEUES["payment"], handle_event)

# Notification 模組中：
consume_events(QUEUES["notification"], handle_event)
```

| handler 結果 | handler 應做的事 | 共用外層處理 |
|---|---|---|
| 業務成功 | 保存業務結果及去重紀錄後正常返回 | ACK |
| 重複事件 | 確認該服務已處理，跳過副作用後返回 | ACK |
| 庫存不足、模擬付款拒絕 | 保存業務失敗結果及處理紀錄後返回 | ACK |
| 格式錯誤、資料庫寫入失敗等技術錯誤 | 拋出例外；不要吞掉例外 | NACK，requeue=False，依既有 DLX 送入 DLQ |

return False 也算正常返回，仍會 ACK。不要用它表示應進 DLQ 的技術失敗。handler 不自行 ACK/NACK，也不需要取得 Pika channel。

去重須按服務分開：Inventory、Payment、Notification 各自記錄 event_id。SQLite 可將本服務的資料更新與去重標記放進同一交易，成功提交後才返回；不能先標記成功才執行業務。這不代表跨服務交易或真實付款具備 exactly-once 保證。

Consumer 技術例外目前送 DLQ，不做自動業務重試。get_connection 的 connection_attempts=3 僅是建立連線時的嘗試；本版沒有執行中斷線自動重連；執行中連線失敗退出時需重新啟動。handler 應保持短時間處理，若需長時間阻塞工作，先與 B 協調心跳與執行方式。

## 8. C、D 預定交付檔案（尚待實作）

以下是建議新增路徑，不是目前已存在的正式業務模組。

| 主責 | 建議路徑 | 要完成的事 |
|---|---|---|
| C | common/event_schema.py | validate_order_created(event)：成功返回 None，無效資料拋 ValueError |
| C | services/order_service.py | create_order(product_id, quantity, unit_price)：驗證、產生識別碼、計算金額、發布 |
| C | services/inventory_service.py | 庫存處理、持久化結果與去重、接入 consume_events |
| D | services/payment_service.py | 模擬付款成功／拒絕、保存結果與去重 |
| D | services/notification_service.py | 記錄「訂單已建立」通知與去重 |

services/__init__.py 由 B 在本次交接文件 PR 中建立空檔；C、D、E 從合併後的 main 開始。每個 Consumer 提供 main 入口和 if __name__ == "__main__"，並說明執行方式。

通知只能說訂單已建立，不能僅收到 OrderCreated 就說付款成功。庫存與付款獨立處理，沒有保證執行先後順序；本版尚無跨服務回滾或補償。

## 9. 提交分支與 Pull Request

每次提交前先檢查：

```powershell
git status
git diff
```

使用 git add 後面列出自己實際修改的檔案，例如 C 完成驗證檔時：

```powershell
git add common/event_schema.py
git diff --cached --name-only
git diff --cached
git commit -m "feat: validate order created events"
```

其餘新增業務檔案也要按實際路徑加入。不要提交 .env、.venv、runtime/ 或資料庫執行資料。

A 第一次推送：

```powershell
git push -u origin docs/research-a
```

E 第一次推送：

```powershell
git push -u origin feature/integration-e
```

C 第一次推送：

```powershell
git push -u origin feature/order-inventory-c
```

D 第一次推送：

```powershell
git push -u origin feature/payment-notification-d
```

之後在同一分支使用 git push。若缺少 Git 提交者名稱／Email，設定本專案的 git config user.name 與 user.email 再提交；不要使用別人的身份。

到 GitHub → Pull requests → New pull request，base 選 main，compare 選自己的分支。填入功能、啟動方式、實際測試結果與尚未完成項目，建立 PR。未完成可開 Draft PR。由小組指定整合者審查及測試後合併；目前若未設分支保護，這是協作約定，不是平台強制限制。

main 有更新時，先提交或妥善保存手邊修改，再在自己的功能分支執行：

```powershell
git fetch origin
git merge origin/main
```

若有衝突先處理，不要直接覆蓋他人的共用程式。合併後重新跑受影響的測試。

## 10. 正式整合的驗收順序

1. 整合者在同一台電腦取得 C、D 的程式、安裝依賴、啟動 Docker 並初始化拓樸。
2. 停止 sample Consumer，避免它與正式服務競爭同一 Queue 的訊息。
3. 在三個終端機分別啟動正式 Inventory、Payment、Notification 模組。若採用上述建議檔名，完成實作後才使用 python -m services.inventory_service 等指令。
4. 使用 C 提供的正式訂單入口建立一筆訂單，確認三個服務收到相同 event_id，各自保存結果後 ACK。
5. 重送同一事件，保持原 event_id，確認庫存不再扣除、付款與通知不重複記錄。
6. 驗證庫存不足／付款拒絕保存業務失敗結果並 ACK，通知文字不誤報付款成功。
7. 驗證技術失敗進入對應 DLQ；未 ACK 斷線後重新投遞，已提交的本機業務不被重複執行。
8. 記錄實測結果，再合併到 main。Analytics 是後續擴充，現有 QUEUES 尚未加入，需先由 B 協助設定。

## 11. 常見狀況

| 狀況 | 先確認 |
|---|---|
| No module named common | 是否從專案根目錄使用 python -m scripts.xxx 或 services.xxx |
| 缺少 RABBITMQ_USER／PASSWORD | 是否建立並儲存本機 .env |
| Connection refused | Docker 是否啟動、容器是否 healthy、5672 是否可用 |
| ACCESS_REFUSED | 帳密、vhost 與既有資料卷的使用者設定是否一致 |
| Consumer 一直等待 | 是否已向同一台 Broker 發布，Queue 是否有訊息，是否被其他 Consumer 取走 |
| PRECONDITION_FAILED | Queue／Exchange 的既有設定是否與程式不同，先交由 B 核對 |
| git push 403／Permission denied | 是否已接受邀請，登入的是否是受邀帳號 |

一般結束本機工作可以使用 docker compose stop；恢復時 docker compose up -d。除非明確要丟棄全部測試資料，不要刪除資料卷。

## 12. 操作依據

- GitHub 邀請協作者：https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository
- 本專案共用傳遞程式：https://github.com/1y0u1y0u/eda-rabbitmq-demo/blob/main/common/messaging.py
- 本專案啟動設定：https://github.com/1y0u1y0u/eda-rabbitmq-demo/blob/main/compose.yaml



## 13. B 本次文件發布步驟

main 保留為共同整合分支，不改名、不刪除。GitHub 頁面選取 main 與 VS Code 目前分支是兩個獨立狀態；網站預設仍顯示 main 是正常的。

1. 在專案根目錄執行 git status。若有尚未保存的修改，先確認內容並保存，不要覆蓋。
2. 工作目錄整理好後執行：

```powershell
git switch main
git pull --ff-only origin main
git switch -c docs/team-handoff
```

若本機已存在 docs/team-handoff，用 git switch docs/team-handoff；不要重複 -c。

3. 將本次修正版兩份檔案放入 docs/project_spec.docx 及 docs/team_handoff.md。舊的 cd_handoff.md 或帶 (1) 的副本移出專案，避免多個有效版本。若舊檔已被 Git 追蹤，將它的刪除也納入此 PR。
4. B 在 VS Code 新建 services 資料夾及空白 services/__init__.py；若已存在就保留，不覆寫。
5. 只加入這次交付檔案：

```powershell
git add docs/project_spec.docx docs/team_handoff.md services/__init__.py
git diff --cached --name-only
git commit -m "docs: align team specification and handoff"
git push -u origin docs/team-handoff
```

6. GitHub 開 Pull Request，base=main、compare=docs/team-handoff。確認修改只包含文件、空的套件標記與必要的舊文件移除；審查後合併。
7. 合併後同步本機：

```powershell
git switch main
git pull --ff-only origin main
```

此時即可通知全組從 main 開工。B 之後要改傳遞程式或補文件時才需要 feature/rabbitmq-b；建立方式如下：

```powershell
git switch -c feature/rabbitmq-b
git push -u origin feature/rabbitmq-b
```

剛建立分支還沒有新的差異時，不必開空 PR。無需由 B 代替 A、C、D、E 建立所有人的分支。

## 14. 全組可直接交給 AI 的共同提示詞

我正在參與 EDA 電商訂單管理系統專題，我的角色是【填 A／C／D／E】。請使用繁體中文協助，依本角色分工逐步完成可執行的成果。

請先讀取附件 project_spec.docx、team_handoff.md，以及儲存庫 https://github.com/1y0u1y0u/eda-rabbitmq-demo 的實際檔案。開始前先列出你確實讀到的分支、提交與檔案；若無法讀取 GitHub，請說明缺少哪些原始檔，不能假裝已閱讀。

先區分已完成與待實作，再列出本角色要新增或修改的精確路徑。統一使用 services/order_service.py、inventory_service.py、payment_service.py、notification_service.py、analytics_service.py，不自行改成 *_consumer.py。

沿用 common/config.py 與 common/messaging.py，不重建獨立 RabbitMQ 傳遞層，不自行更改事件欄位、Queue 名稱、ACK/NACK 政策。publish_event 成功返回 None；handler 正常返回會 ACK，return False 也會 ACK；技術失敗需拋出例外。完整事件驗證、每服務持久化去重及業務結果保存仍待實作。

main 是共同整合分支，請在我自己的功能分支開發，提供逐步操作、必要檔案及測試方式。提出共用檔案或介面修改時，先說明對其他組員的影響；需要配合的工作寫清楚，不能把它當成已完成。

A：完成研究與全系統架構圖，附可靠來源並標示實作範圍。C：先完成驗證與事件範例，確定 create_order 對 E 的回傳契約、P001 初始資料，再接訂單與庫存。D：先固定可重現付款測試方式與紀錄欄位，再完成付款及訂單建立通知。E：先跑通現有測試，與 C 協調介面；完成 README、整合測試與展示計畫；Analytics 需 B 先支援拓樸，Streamlit 可選。

不得捏造測試通過。若你無法在本機執行 Docker 或完整整合測試，請區分已做的靜態／單元檢查與需要我實測的步驟。每次交付列出修改檔案、啟動方式、實測結果、尚未完成事項及 PR 說明。
