"""組員 E 的本機訂單展示介面。"""
from contextlib import closing
from pathlib import Path
import secrets
import sqlite3

from flask import Flask, abort, redirect, render_template_string, request, session, url_for


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
STATUS = {
    "confirmed": ("RabbitMQ 已確認發布", "ok"),
    "failed": ("事件發布失敗", "bad"),
    "unknown": ("無法確認發布結果，請保留事件編號並向組員核對。", "warn"),
}
SERVICE_LABELS = {
    "payment": "付款",
    "notification": "通知",
}
BUSINESS_STATUS = {
    "SUCCESS": "成功",
    "RECORDED": "已記錄",
    "DECLINED": "付款遭拒",
    "DUPLICATE": "重複事件",
    "ERROR": "技術錯誤",
}


def submit_order(create_order, product_id, quantity_text, unit_price):
    """轉換表單數量，將金額文字原樣交給 C 處理精度。"""
    try:
        quantity = int(quantity_text)
    except ValueError:
        return {"publish_status": "invalid", "error": "數量必須是大於 0 的整數。"}

    try:
        result = create_order(product_id.strip(), quantity, unit_price.strip())
    except ValueError as error:
        return {"publish_status": "invalid", "error": str(error)[:300]}

    if (
        isinstance(result, dict)
        and isinstance(result.get("publish_status"), str)
        and result["publish_status"] in STATUS
        and all(isinstance(result.get(key), str) and result[key].strip()
                for key in ("order_id", "event_id"))
    ):
        return {
            "order_id": result["order_id"],
            "event_id": result["event_id"],
            "publish_status": result["publish_status"],
            "error": str(result.get("error") or "")[:300],
        }
    return {
        "publish_status": "unknown",
        "error": "訂單服務回傳格式異常，請查看服務終端機。",
    }


def consumer_results(event_id, runtime_dir):
    """唯讀查詢 D 的已保存紀錄，避免建立或異動服務資料庫。"""
    results = []
    for service, name in SERVICE_LABELS.items():
        path = runtime_dir / f"{service}.sqlite3"
        row = None
        message = "尚未查到已保存的結果。"
        if path.is_file():
            try:
                with closing(sqlite3.connect(
                    f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=1
                )) as connection:
                    row = connection.execute(
                        "SELECT order_id, status, detail, processed_at "
                        "FROM results WHERE event_id = ?",
                        (event_id,),
                    ).fetchone()
            except sqlite3.Error:
                message = "暫時無法讀取紀錄，請查看服務終端機。"
        if row:
            order_id, status, detail, processed_at = row
            message = detail or ""
            status = BUSINESS_STATUS.get(status, status)
        else:
            order_id, status, processed_at = "", "", ""
        results.append((name, status, message, order_id, processed_at))
    return results


def create_app(order_service=None, runtime_dir=RUNTIME_DIR):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    @app.get("/")
    def index():
        if "form_token" not in session:
            session["form_token"] = secrets.token_hex(32)
        result = session.get("last_result")
        event_id = request.args.get("event_id", (result or {}).get("event_id", "")).strip()[:128]
        service_results = consumer_results(event_id, runtime_dir) if event_id else []
        return render_template_string(
            PAGE, result=result, statuses=STATUS, event_id=event_id,
            service_results=service_results, form_token=session["form_token"],
        )

    @app.post("/orders")
    def orders():
        form_token = session.get("form_token")
        submitted_token = request.form.get("form_token", "").encode()
        if not form_token or not secrets.compare_digest(form_token.encode(), submitted_token):
            abort(400, "請從訂單頁面重新開啟表單。")

        service = order_service
        if service is None:
            try:
                from services.order_service import create_order

                service = create_order
            except Exception:
                app.logger.exception("Could not load Order Service")
                session["last_result"] = {
                    "publish_status": "unavailable",
                    "error": "請確認 C 分支已整合，並已安裝專案依賴。詳細原因請看終端機。",
                }
                return redirect(url_for("index"), code=303)

        try:
            result = submit_order(
                service, request.form.get("product_id", ""),
                request.form.get("quantity", ""), request.form.get("unit_price", ""),
            )
        except Exception:
            app.logger.exception("Order Service did not return a publish result")
            result = {"publish_status": "unknown", "error": "訂單服務發生例外，請查看終端機。"}

        session["last_result"] = result
        return redirect(url_for("index"), code=303)

    return app


PAGE = """
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>訂單事件展示</title>
<style>
:root { color-scheme: light; font-family: system-ui, "Microsoft JhengHei", sans-serif;
        color: #18273a; background: #eef3f7; }
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 940px; margin: auto; padding: 36px 20px; }
h1 { margin: 0 0 24px; font-size: clamp(1.8rem, 5vw, 2.6rem); }
h2 { margin: 0 0 18px; font-size: 1.25rem; }
section { background: white; border: 1px solid #d6e1e9; border-radius: 14px;
          padding: 22px; margin-bottom: 18px; }
.fields { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
label { display: grid; gap: 6px; font-weight: 600; }
input, button { font: inherit; border-radius: 8px; padding: 9px 12px; }
input { width: 100%; min-width: 0; border: 1px solid #889aab; }
button { margin-top: 14px; border: 0; background: #14564e; color: white; cursor: pointer; }
button:disabled { opacity: .65; }
:focus-visible { outline: 3px solid #1174ab; outline-offset: 2px; }
small, .hint { color: #465e73; }
.notice { border-left: 4px solid #64788a; padding: 10px 12px; background: #f1f6fa;
          margin-top: 18px; overflow-wrap: anywhere; }
.notice p { margin: 6px 0; }
.ok { border-color: #18745f; background: #eaf7f3; }
.bad { border-color: #a3303d; background: #fbeff0; }
.warn { border-color: #946208; background: #fff6e1; }
.records { margin: 18px 0 0; padding: 0; list-style: none; }
.records li { padding: 10px 0; border-top: 1px solid #d6e1e9; overflow-wrap: anywhere; }
.records .detail { display: block; margin: 4px 0; }
@media (max-width: 580px) { .fields { grid-template-columns: 1fr; } main { padding-top: 20px; } }
</style>
</head>
<body>
<main>
<h1>訂單事件展示</h1>
<section>
<h2>建立測試訂單</h2>
<form method="post" action="{{ url_for('orders') }}" onsubmit="this.querySelector('button').disabled = true">
<input type="hidden" name="form_token" value="{{ form_token }}">
<div class="fields">
<label>商品編號<input name="product_id" value="P001" required maxlength="100"></label>
<label>數量<input type="number" name="quantity" value="1" required min="1" step="1"></label>
<label>單價（TWD）<input name="unit_price" value="500.00" inputmode="decimal" required maxlength="40"></label>
</div>
<button>發布訂單事件</button>
</form>
{% if result %}
{% set state = result.publish_status %}
{% set display = statuses.get(state, ('輸入資料有誤' if state == 'invalid' else '無法載入訂單服務', 'bad')) %}
<div class="notice {{ display[1] }}" role="status">
<strong>{{ display[0] }}</strong>
{% if result.error %}<p>{{ result.error }}</p>{% endif %}
{% if result.order_id %}<p>訂單編號 <code>{{ result.order_id }}</code></p>{% endif %}
{% if result.event_id %}<p>事件編號 <code>{{ result.event_id }}</code></p>{% endif %}
{% if state == 'confirmed' %}<p>庫存、付款及通知結果由各服務分別處理。</p>{% endif %}
{% if state == 'unknown' %}<p>請先查詢事件紀錄，避免重複建立同一筆訂單。</p>{% endif %}
</div>
{% endif %}
</section>
<section>
<h2>查詢服務紀錄</h2>
<form method="get" action="{{ url_for('index') }}">
<label>事件編號<input name="event_id" value="{{ event_id }}" required maxlength="128"></label>
<button>查詢／更新結果</button>
</form>
{% if service_results %}
<ul class="records">
{% for name, status, detail, order_id, processed_at in service_results %}
<li><strong>{{ name }}{% if status %} · {{ status }}{% endif %}</strong>
<span class="detail">{{ detail }}</span>
{% if order_id %}<small>{{ order_id }} · {{ processed_at }}</small>{% endif %}</li>
{% endfor %}
</ul>
{% endif %}
<p class="hint">庫存結果請核對 Inventory 終端機。付款技術錯誤請核對 Payment 終端機與 RabbitMQ 死信佇列。</p>
</section>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
