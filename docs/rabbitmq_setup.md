# RabbitMQ 環境建置與操作說明

更新日期：2026-11-25。主責：B。操作環境：Windows PowerShell。

本文件讓組員依現有專案重現 RabbitMQ 環境、訊息分發、ACK、中斷恢復與 DLQ 測試。正式訂單、庫存、付款與通知模組的開發約定見 [event_contract.md](event_contract.md)，全組工作流程見 [team_handoff.md](team_handoff.md)。

## 1. 核對基準與實測範圍

- 儲存庫：[eda-rabbitmq-demo](https://github.com/1y0u1y0u/eda-rabbitmq-demo)。
- 本版程式核對提交：[`6ab20e977d07daeaf4a6274754ccb9c919e55333`](https://github.com/1y0u1y0u/eda-rabbitmq-demo/commit/6ab20e977d07daeaf4a6274754ccb9c919e55333)。這是教師回饋文件 PR 合併後的 main。
- 已核對：compose.yaml、.env.example、requirements.txt、common/config.py、common/messaging.py、現有 sample／中斷／DLQ 測試程式及 docs/b_messaging_test.md。
- B 先前的通過結果見 [b_messaging_test.md](b_messaging_test.md) 與 [evidence](evidence/)；本次補寫操作文件並未重新執行 Docker、RabbitMQ 或正式業務整合測試。
- 此提交已有 services/__init__.py，但正式業務服務與 common/event_schema.py 尚未加入；本文件的 sample 指令只驗證傳遞，不會扣庫存、模擬付款或寄送通知。

## 2. 環境與版本

| 項目 | 已知設定或紀錄 | 重現時需要補記 |
|---|---|---|
| 作業系統 | B 原測試紀錄為 Windows 11 | 個人實際版本 |
| Python | 原紀錄只寫 Python 3 | 實際完整版本，不推測小版本 |
| Docker | Docker Desktop，使用 Linux containers | Desktop、Engine 與 Compose 實際版本 |
| RabbitMQ 映像 | compose.yaml 固定為 rabbitmq:4.4.1-management | 容器實際 RabbitMQ 版本 |
| Pika | requirements.txt 為 pika>=1.3,<2 | 本機實際安裝版本 |
| python-dotenv | requirements.txt 為 python-dotenv>=1,<2 | 本機實際安裝版本 |
| Python 連線位置 | localhost:5672，vhost=/ | 如改動，須與 B 對齊 |
| 管理介面 | http://localhost:15672 | 使用本機 .env 帳密 |

requirements.txt 尚未完全鎖版。先按現有範圍安裝；B／E 在整合確認後補記實際版本，不直接把其他電腦的整份 pip freeze 覆寫進專案。

若尚未安裝，可使用官方入口：[Git for Windows](https://git-scm.com/downloads/win)、[Python Windows](https://www.python.org/downloads/windows/)、[Docker Desktop Windows](https://docs.docker.com/desktop/setup/install/windows-install/)。Docker 若提示 WSL 2／虛擬化需求，依官方安裝步驟完成並重新開啟終端機。

## 3. 取得專案與準備終端機

已有正確 clone 的人不用重新 clone。新組員先在預定父資料夾執行：

```powershell
git clone https://github.com/1y0u1y0u/eda-rabbitmq-demo.git
cd eda-rabbitmq-demo
git status
```

若同名資料夾已存在，不覆蓋；先確認它是否就是既有專案。各組員依 team_handoff.md 第 3 節建立自己的分支。以下指令都從專案根目錄執行，不是在 docs 或 scripts 資料夾。

先啟動 Docker Desktop，再檢查：

```powershell
git --version
py --version
docker --version
docker compose version
docker info
```

確認 Docker Engine 可連線且使用 Linux containers。若電腦只有 python 沒有 py，先確認 `python --version` 是 Python 3，下面建立虛擬環境時改用 python。

## 4. Python 虛擬環境

第一次、尚未建立 .venv 時執行：

```powershell
py -m venv .venv
```

安裝及確認套件：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show pika python-dotenv
```

本文件直接指定虛擬環境的 python.exe，不需執行 Activate.ps1，也不需為此修改 PowerShell 執行原則。VS Code 可將 Python Interpreter 選為本專案 .venv。

## 5. 建立本機設定

先檢查：

```powershell
Test-Path .env
```

只有結果為 False 才執行：

```powershell
Copy-Item .env.example .env
```

在 VS Code 開啟 .env，內容應包含：

```dotenv
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=eda_user
RABBITMQ_PASSWORD=CHANGE_ME
RABBITMQ_VHOST=/
```

將 CHANGE_ME 換成自己的本機密碼，再儲存。其他組員不必與 B 使用相同密碼。含 `$`、`#` 等特殊字元時需留意 .env 引號及 Compose 插值規則；首次課堂測試可使用自己產生的英數密碼，避免解析差異。

Docker Compose 將 RABBITMQ_USER／PASSWORD／VHOST 傳給容器作初始化；Python 從專案根目錄讀取 .env。已存在的終端機環境變數可能覆蓋 .env，遇到設定不一致時需一併檢查，但不要把實際密碼貼到群組或報告。

確認忽略規則：

```powershell
git check-ignore .env .venv/
```

.env、.venv/、__pycache__/、*.pyc 與 runtime/ 不提交；.env.example 應保留在 GitHub。

**已有資料卷的情況：**預設帳密是在 RabbitMQ 首次初始化空資料目錄時建立。之後只改 .env 不會改掉既有 RabbitMQ 使用者密碼。登入失敗時先請 B 協助確認帳密／權限，不要刪資料卷解決。

## 6. 啟動 RabbitMQ

```powershell
docker compose up -d
docker compose ps
```

等待 rabbitmq 顯示 healthy。若仍是 starting，稍後再查；若失敗，執行：

```powershell
docker compose logs --tail 80 rabbitmq
```

補記實際版本：

```powershell
docker compose exec rabbitmq rabbitmq-diagnostics server_version
```

已知 compose 設定：

- 映像 rabbitmq:4.4.1-management，容器 hostname 為 eda-rabbitmq。
- 宿主機只綁定 127.0.0.1 的 5672、15672。
- 具名資料卷 rabbitmq_data 掛載至 /var/lib/rabbitmq；Docker 實際卷名通常含 Compose 專案前綴。
- 健康檢查為 rabbitmq-diagnostics -q check_running；每 10 秒檢查，timeout 10 秒、retries 12、start_period 30 秒。
- healthy 表示 Broker 健康檢查通過，不代表 Python 帳密、事件拓樸或業務服務已驗證。

在瀏覽器開啟 [RabbitMQ 管理介面](http://localhost:15672)，使用自己的 .env 帳密登入。RabbitMQ 並非共用的雲端服務：每個人的 localhost 都是自己的電腦。開發時各自測試，整合展示建議集中一台電腦；不要只為了整合自行把連接埠開放到外網。

## 7. 建立及核對拓樸

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_rabbitmq
```

預期建立兩個自訂 Exchange（管理頁還會顯示 RabbitMQ 內建 Exchange）：

| Exchange | Type | Durable |
|---|---|---|
| ecommerce.events | topic | true |
| ecommerce.dlx | direct | true |

主 Queue 都以 order.created 綁定到 ecommerce.events。每個 Queue 都是 classic、durable、非 exclusive、非 auto-delete。

| 主 Queue | DLQ | 進入 DLX 後使用的 routing key |
|---|---|---|
| inventory.order-created | inventory.order-created.dlq | inventory.order-created |
| payment.order-created | payment.order-created.dlq | payment.order-created |
| notification.order-created | notification.order-created.dlq | notification.order-created |

主 Queue 設定 x-dead-letter-exchange=ecommerce.dlx，並以原主 Queue 名稱作 x-dead-letter-routing-key。DLQ 綁定到 ecommerce.dlx。現有程式使用宣告參數維護設定，請勿自行改成不相容的 Queue 型別或屬性。

在管理頁的 Exchanges、Queues and Streams 與 Bindings 核對名稱。也可從終端機查看計數：

```powershell
docker compose exec rabbitmq rabbitmqctl list_queues -p / name messages_ready messages_unacknowledged consumers
```

若使用非預設 vhost，上面 `/` 需換成自己的設定。setup 可在相同設定下重複執行；若出現 PRECONDITION_FAILED，代表已有物件設定不相容，先交由 B 比對，不要直接刪 Queue。發布及接收函式不會自動替你建立完整拓樸，首次執行一定先做 setup。

## 8. 基本傳遞測試

先停止所有正式／sample Consumer，避免訊息被其他程序取走。下列精確計數適用於乾淨、無其他發布者的測試環境；若 Queue 已有訊息，先記錄基準並確認用途，不任意清空，也不要假設 --once 收到的就是剛發布的事件。

### 8.1 發布一次

```powershell
.\.venv\Scripts\python.exe -m scripts.publish_sample
```

記下 event_id 與 order_id。預期印出 RabbitMQ 已確認、未回報無法路由，三個主 Queue 的 Ready 各增加 1。

### 8.2 接收及觀察 ACK

先執行庫存 sample，等待期間可切到管理頁觀察 Unacked：

```powershell
.\.venv\Scripts\python.exe -m scripts.consume_sample --service inventory --ack-delay 30 --once
```

再依序執行：

```powershell
.\.venv\Scripts\python.exe -m scripts.consume_sample --service payment --once
.\.venv\Scripts\python.exe -m scripts.consume_sample --service notification --once
```

比對三者收到相同 event_id，均顯示 ACK SENT。若起初完全空白，處理完成後三個主 Queue 回到 Ready=0、Unacked=0，DLQ 不應新增。

--once 表示「接收並處置一筆後結束」，不是無訊息就結束；一直等待時先確認 Queue 是否有訊息。sample 只驗證部分欄位並印出內容，不是完整事件驗證器，也不會執行業務。

## 9. 中斷恢復及 DLQ 測試

以下沿用現有測試程式，須在可辨識訊息及無競爭 Consumer 的環境執行；執行後會產生測試資料。

### 9.1 未 ACK 中斷

先發布一筆新事件：

```powershell
.\.venv\Scripts\python.exe -m scripts.publish_sample
.\.venv\Scripts\python.exe -m scripts.hold_unacked --service inventory
```

記下 event_id，觀察 inventory 的 Unacked=1。於該終端機按 Ctrl+C 關閉連線，確認未 ACK 訊息重新回到 Ready。再執行：

```powershell
.\.venv\Scripts\python.exe -m scripts.consume_sample --service inventory --once
```

核對同一 event_id、重新投遞標記為 True、最後 ACK。另以 payment／notification 的 --once 接收各自那份事件，避免留下本輪主 Queue 測試訊息。

此測試驗證未 ACK 連線關閉後重新投遞，不等於 Broker 重啟測試，也不代表已驗證業務去重。

### 9.2 格式錯誤送 DLQ

先確保 inventory 主 Queue 沒有其他待處理訊息，記下 DLQ 基準，再執行：

```powershell
.\.venv\Scripts\python.exe -m scripts.publish_invalid_sample
.\.venv\Scripts\python.exe -m scripts.consume_sample --service inventory --once
```

預期錯誤為缺少 data.order_id；consumer 顯示 NACK，inventory.order-created.dlq 較原計數增加 1。

publish_invalid_sample 刻意走預設 Exchange，僅送 inventory 主 Queue，並使用測試 producer。它是注入無效資料的測試工具，不是 C 正式發布的示範；不能拿它證明 publish_event 會驗證所有訂單欄位。

此輪 DLQ 訊息應保留供查看。完成後不能聲稱六個 Queue 全部為空。不要把 DLQ 訊息自動重送；修復與重送流程需由 B 和業務主責確認。

## 10. 停止及再次開工

先在各 Consumer 終端機按 Ctrl+C，再停止 Broker：

```powershell
docker compose stop
```

下次恢復：

```powershell
docker compose up -d
docker compose ps
```

健康檢查通過後啟動所需服務。`docker compose down` 會移除本專案容器與網路，通常保留此處的具名資料卷；一般暫停使用 stop 即可。**不要把 `docker compose down -v` 當成一般重啟，它會刪除此專案具名資料卷與其中的 RabbitMQ 資料。**

## 11. 常見問題

| 現象 | 檢查與處理 |
|---|---|
| 無法連到 Docker daemon | 開啟 Docker Desktop，確認 Linux Engine 已就緒 |
| 5672／15672 已被占用 | 確認是否有另一個 RabbitMQ／Compose 專案；協調停止或由 B 調整設定，勿隨意終止不明程序 |
| Compose 提示缺少變數 | 確認根目錄 .env 已儲存，USER 與 PASSWORD 非空；不公開包含密碼的設定輸出 |
| Connection refused | 容器是否運作、host／port 是否正確；healthy 後再測試 Python |
| ACCESS_REFUSED | 核對本機帳密、vhost、權限及舊資料卷，改 .env 不等於改既有帳密 |
| No module named common | 回專案根目錄，使用虛擬環境 python.exe 與 -m scripts.xxx |
| 找不到 pika／dotenv | 確認 pip 與執行程式使用同一個 .venv Python |
| PRECONDITION_FAILED | 已有 Queue／Exchange 設定不相容，先交 B 比對，不刪資料硬重建 |
| Consumer 一直等待 | Queue 無訊息、已被別的 Consumer 消費、或發布到另一台 Broker |
| --once 接收到舊訊息 | 有歷史積壓；以 event_id 核對，不假定第一筆就是本輪事件 |
| 發布確認但少一個服務未收到 | 檢查該 Queue／Binding、其他 Consumer 及服務紀錄；mandatory 不保證所有預期 Queue 均存在 |
| DLQ 測試後還有 Ready | 可能就是預期保留的無效訊息；先核對 Queue 名稱與 event_id |

執行中斷線後，現有 consumer 沒有自動重連。get_connection 的 connection_attempts=3、retry_delay=2 僅是建立連線階段的嘗試；目前也沒有自動業務 Retry Queue。

## 12. 測試紀錄及教師要求

每次新增實測，在原負責文件記錄日期、提交、實際版本、前置資料、步驟、預期／實際結果、event_id 與證據路徑。不要改寫原有通過紀錄，也不要把本文件中的預期結果當成新測試結果。

B 的歷史證據：b_01～b_18（b_09 未拍攝），維持原檔名。正式業務整合結果由 E 整理到 docs/integration_test.md，D 的業務紀錄規格放 docs/event_processing_log.md。

教師要求說明模組依賴與 EDA 改善。暫停某 Consumer、保留訊息、恢復後接收可支持時間解耦的論點，但必須說明 Broker 與既有拓樸正常的前提。sample 只能支持傳遞層論點；正式服務展示依 team_handoff.md 第 15 節。不得宣稱已具備全業務成功、跨服務交易或永不丟訊息的保證。

## 13. 來源

專案行為以本文件所列提交的程式為準；官方文件協助理解機制，不代表官方範例與本專案設定完全相同。

- [專案 compose.yaml](../compose.yaml)、[共用設定](../common/config.py)、[共用傳遞程式](../common/messaging.py)。
- [RabbitMQ Publish/Subscribe](https://www.rabbitmq.com/tutorials/tutorial-three-python)。
- [RabbitMQ Consumer ACK 與 Publisher Confirm](https://www.rabbitmq.com/docs/confirms)。
- [RabbitMQ Dead Letter Exchanges](https://www.rabbitmq.com/docs/dlx)。
- [Docker Compose 環境變數插值](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)。
