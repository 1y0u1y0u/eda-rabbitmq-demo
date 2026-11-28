# 組員 E 整合測試

## 實際驗證範圍

GitHub 核對版本為 `main/3440247`、C 的 `80d886c`、D 的 `49e4282`、B 的 `03d4c36`。C 的 `create_order()` 依約定回傳發布狀態並接受金額字串。D 的付款模式是 `success`、`decline`、`error`，付款和通知結果存在各自的 SQLite `results` 表。C 的庫存版目前更新 `data/products.json`，請用測試副本，將實際檔案位置與重置方式交給 C 確認。

已在 Python 3.12、Flask 3.1.2 執行 E 的自動測試，涵蓋瀏覽流程、發布狀態、輸入拒絕、唯讀查詢、回應後重新整理，以及 Analytics SQLite 去重。測試替身產生的回傳與本機暫存 SQLite 僅供驗證 E 程式。下列 RabbitMQ 端到端情境待在整合環境執行。

## 跨服務整合驗證

以 `main@3440247` 為底，加入 C 的 `80d886c`、D 的 `49e4282` 與 E 的檔案。逐一比對三份快照的同名檔案，內容一致，無須覆蓋任何共用檔案。B 的 `03d4c36` 是另外提出的文件 PR。

在 Python 3.12、Flask 3.1.2、Pika 1.3.2、python-dotenv 1.2.1 執行 `python -B -m unittest discover -s tests -v`，共 17 項 unittest 通過，其中 3 項是 E 新增的跨模組驗證。測試透過 Flask 提交表單，使用 C 的真實訂單與庫存程式、B 的發布與消費回呼、D 的付款和通知程式。Pika 連線及 channel 由測試替身提供，再把實際序列化的事件交給各 Consumer。測試使用暫存庫存檔、SQLite 及 JSONL，保留正式資料。

| 驗證 | 結果 |
|---|---|
| 同一事件送入三個 Consumer | `EVT4F44EFFBB473` 讓 P001 從 10 降為 8，付款為 SUCCESS、通知為 RECORDED，三個分支均呼叫 ACK。E 查詢頁顯示付款成功及通知已記錄。 |
| 通知稍後處理與去重 | 先執行庫存、付款，通知查詢尚無紀錄。呼叫通知 Consumer 後，同一事件可查到通知。重複呼叫三個 Consumer 後，庫存維持 8，付款及通知各有一筆原始結果。 |
| 付款拒絕及技術例外 | 模擬付款拒絕保存 DECLINED 並呼叫 ACK。技術例外寫 ERROR，呼叫 NACK 且 `requeue=False`。 |
| 庫存不足 | P001 有 10 件時送 11 件，庫存未變。C 的 handler 拋出 `ValueError`，B 的回呼呼叫 NACK 且 `requeue=False`。這與交接規格的業務失敗記錄後 ACK 有差異，需由 C 與 B 對齊。 |

這次測試涵蓋程式的 ACK／NACK 呼叫與跨服務的共同 event_id。待在實際 RabbitMQ 環境補驗通知 Queue 的 Ready、Broker Confirm、DLQ 入列及斷線後重新投遞。

## 測試前準備

依 [README](../README.md) 在同一台電腦啟動服務。記錄合併版本、Python／Flask／RabbitMQ 版本及每個 Queue 的 Ready、Unacked、DLQ 基準。停止 sample Consumer。為使 Queue 計數可比較，測試期間只操作本次訂單，先讓相關服務處理已知積壓，並保留既有資料。P001 的種子數量是 10，實際數量以測試前讀值為準。

## 端到端情境

| ID | 操作 | 驗收與證據 | E 實測 |
|---|---|---|---|
| E01 正常流程 | 啟動三個 Consumer，付款使用 `--mode success`，送一筆有效訂單 | App 顯示 confirmed。記錄同一 event_id 的庫存扣減、付款 SUCCESS、訂單建立通知與 ACK | 待實測 |
| E02 省去同步等待 | 停止 Notification，保留 Inventory、Payment。發新單並記錄 Ready，隨後啟動 Notification | 發布已確認，庫存與付款仍可處理。無其他流量時通知 Ready 增 1，啟動後同一事件處理並 ACK，Ready 回到基準 | 待實測 |
| E03 付款拒絕 | 停止原付款服務，等前一筆處理完，使用 `--mode decline`，發新單 | 同一 event_id 有 DECLINED 紀錄且 ACK，付款 DLQ 無該事件。通知只描述訂單成立 | 待實測 |
| E04 付款技術例外 | 改用 `--mode error`，發另一筆新單，完成後切回 success | Payment 終端機有錯誤與 NACK，`payment.order-created.dlq` 收到該事件，付款 results 無完成資料列 | 待實測 |
| E05 輸入驗證 | 分別送空白 ID、非正整數數量及負單價的測試資料。瀏覽器可能先擋下非法數量 | 畫面提示輸入有誤。使用測試程式驗證被拒絕資料，並核對測試前後沒有新增事件 | 待實測 |
| E06 去重 | 由 C／B 在隔離測試環境重送已處理的原事件及原 event_id，先記錄庫存和 D 的資料列 | 各服務略過重複副作用，庫存及原紀錄保持，訊息仍由共用層 ACK | 待實測 |
| E07 庫存不足 | 讀取當下庫存，用有效商品送超過庫存的數量 | Inventory 有失敗證據且庫存未減。規格預期記錄業務失敗後 ACK，請記下 C 當前版的實際 ACK／NACK 行為並交給 C 確認。付款仍可能獨立處理 | 待實測 |
| E08 新增訂閱 | B 完成拓樸後啟動 Analytics，發布一筆新單，記錄基準和新統計。由 C／B 重送同 ID | 新增 1 筆及對應金額，重送後總數和總額相同。保留擴充前後 Git 差異與 console 紀錄 | 待 B 拓樸及實測 |

錄證時使用正常頁面、服務終端機與 RabbitMQ 頁面。若需查看 DLQ 訊息內容，使用管理介面可重入列的讀取方式，保留證據。

## 發布狀態與紀錄方式

`confirmed` 表示 Broker 已確認此發布。付款模式 `decline` 仍可出現 confirmed，因為發布與付款是各自獨立的結果。`failed` 和 `unknown` 可由自動測試穩定重現，真實故障測試另由 B、C 與 E 在隔離環境驗證。遇到 `unknown` 保留原事件編號並核對紀錄，重試由 C／B 沿用原事件。

每筆用下表留證，應可依同一 event_id 回查整段流程。

| 情境 | 時間與提交 | order_id / event_id | 發布結果與服務紀錄 | Queue／DLQ 前後 | 截圖路徑 | 結論 |
|---|---|---|---|---|---|---|
| E__ | 待填 | 待填 | 待填 | 待填 | 待填 | 待實測 |

## 教師回饋對應

| 依賴 | 同步比較案例 | EDA 機制 | 證據 |
|---|---|---|---|
| 呼叫介面 | 訂單依序直接呼叫庫存、付款、通知 | Order Service 發出共同事件，各服務訂閱自己的 Queue | C 的發布程式與 A 的架構圖 |
| 時間與可用性 | 通知服務變慢或離線可能延後呼叫端返回 | 在 Broker 和 Binding 正常時，通知服務可稍後消費等待中的訊息 | E02 的同一 event_id 和 Queue 基準 |
| 擴充時的修改 | 增加統計步驟會修改示意中的訂單呼叫流程 | 增加 Analytics Queue、Binding 及 Consumer 即可接收新事件 | E08 的 Git 差異與累計結果 |

系統仍依賴 Broker、事件契約及拓樸。重複投遞須各服務處理，庫存和付款各自完成且可能暫時不一致，本版未提供跨服務補償。
