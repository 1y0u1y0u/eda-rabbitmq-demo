# A、B、C、D、E 全組操作與整合說明

更新日期：2026-11-25，教師回饋增補版。適用環境：Windows PowerShell。

**本次更新：請全組加讀第 15 節；原分工、正式檔名、事件格式及共用介面維持不變。第 13 節已改為本次更新操作。**

儲存庫：https://github.com/1y0u1y0u/eda-rabbitmq-demo

本說明先前已核對下列提交中的 compose.yaml、.env.example、requirements.txt、common/config.py、common/messaging.py 及測試程式。B 已在自己的電腦完成傳遞測試；C、D 仍需在各自電腦驗證環境。本文件不代表正式庫存、付款或通知功能已完成。


## 0. 本版統一事項與目前進度

本文件搭配 `docs/project_spec.docx` 使用，取代舊 `cd_handoff.md`。請勿同時將舊版交接檔當成有效規格。檔名中的 `(1)` 只是下載時的重複檔名後綴，不是正式版本號。

先前程式核對基準為 GitHub `main` 的提交 `651998a0bd62f4f06c164f0e388a96cafe24d593`，核對時遠端只有 main。此為歷史基準；本次僅增補文件，不宣稱已重新檢查遠端進度。開工請以最新 main 及實測紀錄確認完成狀態。

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

services/__init__.py 由 B 在首次交接文件 PR 中建立空檔；C、D、E 從合併後的 main 開始。每個 Consumer 提供 main 入口和 if __name__ == "__main__"，並說明執行方式。

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



## 13. B 本次教師回饋文件更新步驟

本次只更新 `docs/project_spec.docx` 與 `docs/team_handoff.md`。`main` 保留為共同整合分支，不改名。先前首次交接 PR 若尚未合併，先完成該 PR；已有的 services/__init__.py 不必重建。

1. 在專案根目錄執行 `git status`。若有未提交修改，先確認並保存到原工作分支，不要用 reset 或覆蓋來清除。
2. 工作目錄乾淨後，取得最新 main，再建立本次文件工作分支：

```powershell
git switch main
git pull --ff-only origin main
git switch -c docs/teacher-feedback
```

若分支已存在且是這次尚未完成的工作，使用 `git switch docs/teacher-feedback`，再以 `git merge main` 同步剛更新的 main；有衝突先解決，不強制覆蓋。

3. 用新版兩份檔案取代專案內同名檔案。保留正式檔名，不使用下載時自動增加的 `(1)`。確認位置不是 docs/docs/，也不是雙重副檔名。若其他組員已更新這兩份文件，先比對並保留對方新增內容。
4. 檢查並提交，這次只加入兩份文件：

```powershell
git status
git diff -- docs/team_handoff.md
git add docs/project_spec.docx docs/team_handoff.md
git diff --cached --name-only
git commit -m "docs: add teacher feedback on module dependencies"
git push -u origin docs/teacher-feedback
```

5. 到 GitHub 的 Pull requests 建立 PR，base 選 main，compare 選 docs/teacher-feedback。檢查 Files changed 僅含這兩份文件；Word 在 GitHub 可能不顯示文字差異，需下載或本機開啟核對。審查後 Merge pull request → Confirm merge。
6. 合併後同步本機：

```powershell
git switch main
git pull --ff-only origin main
git status
```

7. 通知全組更新文件。尚未開始的人從最新 main 建立自己原定的分支。已在工作分支的人，先提交並保存自己的修改，保持工作目錄乾淨，再在自己的分支執行：

```powershell
git fetch origin
git merge origin/main
```

若發生文件衝突，保留雙方內容並協調解決。不要為更新文件重新 clone 或刪除原工作分支。`docs/teacher-feedback` 是 B 此次的臨時文件分支；組員沿用各自原定分支。確認 PR 已合併後，可刪除這個臨時分支。

## 14. 全組可直接交給 AI 的共同提示詞

我正在參與 EDA 電商訂單管理系統專題，我的角色是【填 A／C／D／E】。請使用繁體中文協助，依本角色分工逐步完成可執行的成果。

請先讀取附件 project_spec.docx、team_handoff.md，以及儲存庫 https://github.com/1y0u1y0u/eda-rabbitmq-demo 的實際檔案。開始前先列出你確實讀到的分支、提交與檔案；若無法讀取 GitHub，請說明缺少哪些原始檔，不能假裝已閱讀。

先區分已完成與待實作，再列出本角色要新增或修改的精確路徑。統一使用 services/order_service.py、inventory_service.py、payment_service.py、notification_service.py、analytics_service.py，不自行改成 *_consumer.py。

沿用 common/config.py 與 common/messaging.py，不重建獨立 RabbitMQ 傳遞層，不自行更改事件欄位、Queue 名稱、ACK/NACK 政策。publish_event 成功返回 None；handler 正常返回會 ACK，return False 也會 ACK；技術失敗需拋出例外。完整事件驗證、每服務持久化去重及業務結果保存仍待實作。

main 是共同整合分支，請在我自己的功能分支開發，提供逐步操作、必要檔案及測試方式。提出共用檔案或介面修改時，先說明對其他組員的影響；需要配合的工作寫清楚，不能把它當成已完成。

A：完成研究與全系統架構圖，附可靠來源並標示實作範圍。C：先完成驗證與事件範例，確定 create_order 對 E 的回傳契約、P001 初始資料，再接訂單與庫存。D：先固定可重現付款測試方式與紀錄欄位，再完成付款及訂單建立通知。E：先跑通現有測試，與 C 協調介面；完成 README、整合測試與展示計畫；Analytics 需 B 先支援拓樸，Streamlit 可選。

教師已同意題目，但要求清楚解釋傳統架構的模組依賴，以及 EDA 如何改善。請依 project_spec.docx 第十一至十三節與本文件第 15 節，把依賴問題、機制、實測證據與限制納入我的原定交付物。不改主責與檔名，不把同步示意當成已實作，也不宣稱 EDA 消除所有依賴。

不得捏造測試通過。若你無法在本機執行 Docker 或完整整合測試，請區分已做的靜態／單元檢查與需要我實測的步驟。每次交付列出修改檔案、啟動方式、實測結果、尚未完成事項及 PR 說明。

## 15. 教師回饋補充與全組執行重點

### 15.1 教師要求與本次範圍

教師回覆題目沒有問題，並要求「特別清楚說明傳統架構存在的模組依賴問題，以及 EDA 如何解決該問題」。本次補強報告論證、架構比較與展示驗收；原 A～E 主責、檔名、事件欄位與共用介面不變。教師未在這則回信中要求另做完整同步系統或重新提交綱要。

以下展示是小組為回應要求選定的方式，不是教師指定的唯一方法；同步程式示範為選做。Analytics 維持原第二階段規劃及 E 確認承接的安排。

### 15.2 報告應回答的問題

比較案例固定為「訂單模組依序直接呼叫庫存、付款與通知，等待各步驟返回」。請明確標示它是選定的同步案例，不代表所有傳統架構，也不要將單體／微服務直接等同同步／非同步。

| 依賴問題 | 同步案例 | EDA 改善 | 可用證據 |
|---|---|---|---|
| 呼叫介面依賴 | 訂單模組知道下游呼叫介面，介面修改可能牽動呼叫端 | 訂單發布共同事件，各服務透過自己的 Queue 訂閱 | 同步與 EDA 對照圖、訂單程式未直接呼叫 Consumer handler |
| 時間與可用性依賴 | 下游慢或不可用，可能造成等待、逾時或錯誤，依原錯誤處理而定 | Broker 與既有拓樸正常時，發布不用等待所有 Consumer 完成 | 通知暫停時其他服務處理、Ready 累積、通知恢復後處理同一 event_id |
| 擴充修改依賴 | 在訂單流程直接加入統計呼叫會修改該流程 | 新增訂閱者接收既有事件，訂單發布邏輯可保持不變 | 第二階段 Analytics 結果與 Git 修改清單 |

必須說明：EDA 降低耦合，並未消除依賴。仍依賴 Broker、事件契約、Queue／Binding 與本專案的共用程式。發布成功不是付款成功或訂單全部完成；跨服務結果可能暫時不一致，需要去重、追蹤與錯誤處理。本版沒有跨服務回滾或補償，不宣稱完整交易一致性、必然更快或永不丟訊息。

### 15.3 沿用原分工補強交付內容

| 組員 | 沿用檔案 | 補強內容 |
|---|---|---|
| A | docs/eda_research.md；docs/system_architecture.mmd、.png | 加入依賴分析、三項對照、限制與來源；在既有架構檔清楚分區呈現同步案例與 EDA，同步部分標示為示意 |
| B | docs/b_messaging_test.md；docs/message_flow.mmd、.png | 對應現有傳遞證據與架構論點，協助正式服務暫停／恢復及拓樸展示；保留舊紀錄、截圖檔名，不把舊測試當成新的業務驗收 |
| C | services/order_service.py；services/inventory_service.py | 依原分工完成，維持發布事件而非直接呼叫各 Consumer；提供發布與庫存證據 |
| D | services/payment_service.py；services/notification_service.py；docs/event_processing_log.md | 依原分工完成，提供服務啟停、付款及通知紀錄；通知只表示訂單建立 |
| E | docs/integration_test.md；docs/demo_script.md；report/final_report.docx；report/final_slides.pptx | 統整問題、架構比較、機制、實測、限制；收集同一 event_id 的證據，安排展示 |

不另增必交檔名。既有內容保留，在各自原交付物內補充。若一個架構圖檔同時呈現兩種設計，請分區並清楚標示，避免把示意的同步模組誤認為已存在的程式。

### 15.4 展示一 通知服務暫停與恢復

**目標：**證明在本次測試前提下，發布及其他服務處理不必等待 Notification 同時在線。

**前提：**同一台測試電腦、Broker 正常，三個主 Queue 與 Binding 已建立；記錄原 Queue 計數，準備有效商品及可成功處理的付款條件。停止 sample Consumer，且確認沒有其他 Consumer 消費通知 Queue。不要清空既有資料來湊出預期數字。

1. 啟動正式 Inventory 與 Payment，停止正式 Notification。
2. 使用 C 的正式訂單入口發布一筆新事件，記下 event_id、order_id 與發布結果。
3. 核對庫存、付款服務保存結果並 ACK；通知 Queue 的 Ready 較基準增加 1，且尚無該事件的通知處理紀錄。
4. 啟動 Notification，確認處理同一 event_id、保存訂單建立通知並 ACK。無其他流量時，Ready 回到基準。
5. E 在 docs/integration_test.md 記錄測試前提、步驟、預期／實際結果、證據路徑與結論，並將現場順序加入 docs/demo_script.md。B、C、D 提供各自證據。

如果有既有積壓訊息，以 event_id 對照，不只看 Queue 數量。正式業務尚未完成前，可用 sample 程式預演，但只能稱傳遞層測試，不能稱正式庫存／付款／通知已驗收。實際啟動指令以完成的模組入口為準，不新增尚不存在的訂單 CLI 參數。

**結論界線：**可以說通知暫停沒有阻止這次發布及其他消費者處理；不可說此時所有業務已完成，或 Broker 故障也毫無影響。

### 15.5 展示二 新增 Analytics 訂閱

沿用原第二階段規劃，E 先確認承接。B 加入 QUEUES、Analytics Queue、Binding 與對應 DLQ，E 完成 services/analytics_service.py。建立綁定後發布新事件，核對統計結果。

保留擴充前後的 Git 差異與修改清單，說明 services/order_service.py 的發布邏輯未因新增訂閱而修改；同時誠實列出拓樸設定、新服務與文件的變更。不能宣稱整個專案完全不用改，也不能宣稱新 Queue 自動補收歷史事件。未完成時標示待實作。

### 15.6 報告安排與驗收

建議在原報告與簡報中安排：問題情境 → 同步呼叫依賴 → EDA 架構與機制 → 實測證據 → 仍存在的限制。這是原成果的內容補強，不新增整套交付要求。

驗收時確認：

- 至少清楚說明呼叫介面、時間／可用性及擴充修改三類依賴。
- 每項改善都能對應機制或程式；需實測的主張附實際紀錄。
- 架構示意、預期結果、實際結果分開標示，不捏造測試通過。
- 同一展示以 event_id 串起發布、Queue 狀態與服務紀錄。
- 不用「EDA 發布確認耗時」對比「同步全部業務完成耗時」就宣稱整體效能提升；如量測，明確區分兩種指標及條件。
- 說明 Broker、事件契約、共用程式、去重及跨服務一致性限制。

本次文件更新未執行新測試，原有測試只支持原紀錄中的情境。

### 15.7 交給 AI 的補充提示

請接續我的原角色工作，先閱讀 project_spec.docx 第十一至十三節與 team_handoff.md 第 15 節。老師要求我們清楚說明傳統架構的模組依賴問題，以及 EDA 如何改善。

請依我的原分工與原檔名，在既有交付物中加入「具體依賴問題、EDA 對應機制、所需實測證據及限制」。不要改事件格式、共用傳遞介面、服務命名或其他人的分工。同步架構是比較示意；除非另行決定，不建立完整同步系統，也不加入新的跨服務交易方案。若不能執行測試，請提供操作與待驗證清單，不得寫成已通過。

### 15.8 參考資料

- RabbitMQ Publish/Subscribe：https://www.rabbitmq.com/tutorials/tutorial-three-python
- Microsoft Azure Architecture Center Event-driven architecture：https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven
