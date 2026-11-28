# EDA 電商訂單事件展示

這個專題使用 Python 和 RabbitMQ 示範電商訂單的事件驅動架構。操作頁呼叫 C 的 `create_order()`，RabbitMQ 將 `OrderCreated` 分發給庫存、付款和通知服務，各自保存或顯示處理結果。

## 開始前

- 從專案根目錄執行下列 PowerShell 指令。請先啟動 Docker Desktop，並使用同一台電腦上的 RabbitMQ、操作頁與各業務服務。
- GitHub 核對基準為 `main`（`3440247`）、`feat/c-order-inventory`（`80d886c`）、`feature/payment-notification-d`（`49e4282`）及 `feature/rabbitmq-b`（`03d4c36`）。正式整合前先確認 C、D 的變更已進入你手上的測試版本。A、B 已有內容可在倉庫查閱。
- 操作頁新增 Flask 依賴，由 E 的安裝步驟補上。RabbitMQ 與其他組員的 Python 依賴沿用 `requirements.txt`。

## 安裝與啟動

第一次設定：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt "Flask>=3.1,<4"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

編輯本機 `.env`，依 B 的 `docs/team_handoff.md` 設定 RabbitMQ 帳密。已用過的 RabbitMQ 資料卷需使用原本可登入的帳密。接著啟動：

```powershell
docker compose up -d
docker compose ps
```

等 RabbitMQ 顯示 `healthy`，再執行：

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_rabbitmq
```

管理介面網址為 [localhost:15672](http://localhost:15672)。正式服務各開一個 PowerShell，停掉同一個主 Queue 上的 sample Consumer：

| 終端機 | 啟動指令 |
|---|---|
| 庫存 | `.\.venv\Scripts\python.exe -m services.inventory_service` |
| 付款 | `.\.venv\Scripts\python.exe -m services.payment_service --mode success` |
| 通知 | `.\.venv\Scripts\python.exe -m services.notification_service` |
| 訂單頁 | `.\.venv\Scripts\python.exe app.py` |

開啟 [127.0.0.1:5000](http://127.0.0.1:5000)，輸入有效商品、正整數數量及單價。示範可使用 P001、1、500.00，請先確認實際庫存。

## 查看訂單與服務結果

| 顯示 | 意義 |
|---|---|
| RabbitMQ 已確認發布 | 查看 `order_id` 與 `event_id`，再查各服務結果 |
| 事件發布失敗 | 依畫面原因查看 Broker、路由或服務終端機 |
| 無法確認發布結果 | 保留原 `event_id` 並查紀錄。若需重試，與 C／B 協調重送原事件 |
| 輸入資料有誤 | 修正欄位後再提交 |

用同一個 `event_id` 在頁面查詢付款、通知的 SQLite 紀錄。庫存請查 Inventory 終端機。技術例外看 Payment 終端機和對應 DLQ。頁面以唯讀方式查詢 `runtime/payment.sqlite3` 和 `runtime/notification.sqlite3`。頁面顯示尚無紀錄時，可以重新查詢，或核對服務是否已收到該事件。

C 分支目前會更新 `data/products.json`。請在本機驗收副本測試，先記錄庫存，避免把測試造成的資料變更加入 E 的提交。

## 測試與展示

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_member_e.py -v
```

C、D 的程式已放入同一份測試副本時，可再執行 `python -m unittest discover -s tests -p test_e_integration.py -v`。這批測試用真實服務程式與模擬的 RabbitMQ 連線，正式 Broker 驗收仍依整合測試紀錄執行。

- [整合測試與紀錄表](docs/integration_test.md)
- [現場展示與錄影腳本](docs/demo_script.md)
- Analytics 是第二階段展示。B 加入 `QUEUES["analytics"]`、`analytics.order-created`、Binding 與對應 DLQ 後，重跑拓樸初始化，再執行 `.\.venv\Scripts\python.exe -m services.analytics_service`。該服務統計有綁定後收到的訂單事件金額，包含付款尚未完成或遭拒的訂單事件。

## 分工

| 組員 | 負責內容 |
|---|---|
| A | EDA 研究和架構圖 |
| B | RabbitMQ、共用傳遞層與傳遞測試 |
| C | 訂單、事件驗證與庫存 |
| D | 付款、通知與處理紀錄 |
| E | 操作頁、整合測試、成果展示與第二階段 Analytics 接收端 |

驗收及展示請保留事件 ID 和必要截圖。Git 提交時依分工選檔，排除本機 `.env`、`.venv`、`runtime/` 與測試後的庫存資料。

## 組員 E 提交

在自己的 `feature/integration-e` 分支使用此包的專案相對路徑。若分支已存在，切換至既有分支即可。複製前先檢查同名檔，已有內容請先比對。正式整合最好等 C、D 的 PR 合併，或與組員確認獨立驗收副本使用哪些提交。

```powershell
git status --short
git add -- app.py README.md docs/integration_test.md docs/demo_script.md services/analytics_service.py tests/test_member_e.py tests/test_e_integration.py
git diff --cached --name-only
git diff --cached --check
```

`report/member_e_report.docx` 和 `report/member_e_slides.pptx` 供整併到小組的期末報告和簡報。PR 說明可附自動測試結果、正式整合待驗收項目，以及 Analytics 需要 B 配置的拓樸。
