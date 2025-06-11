from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import sqlite3
from dotenv import load_dotenv
import os
from fyers_client import get_ltp, place_order

load_dotenv()
DB_FILE = "alerts.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
app = FastAPI()

class ChartinkAlert(BaseModel):
    stocks: str
    trigger_prices: float
    side: str
    timestamp: str
    alert_id: str

@app.post("/api/chartink-alert")
async def receive_alert(alert: ChartinkAlert, background_tasks: BackgroundTasks):
    try:
        cursor.execute("INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?)", (
            alert.alert_id,
            alert.stocks.upper(),
            alert.trigger_prices,
            alert.side.lower(),
            alert.timestamp,
            "PENDING"
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        return {"status": "duplicate", "id": alert.alert_id}

    background_tasks.add_task(process_alert, alert.alert_id)
    return {"status": "received", "id": alert.alert_id}

def process_alert(alert_id):
    cursor.execute("SELECT stock, trigger_price, side FROM alerts WHERE alert_id=?", (alert_id,))

    row = cursor.fetchone()
    if not row:
        return
    symbol, price, side = row
    fyers_symbol = f"NSE:{symbol}-EQ"
    qty = 100
    sl_buffer = 0.02
    tp_buffer = 0.05

    if side == "long":
        stop_loss = round(price * (1 - sl_buffer), 2)
        take_profit = round(price * (1 + tp_buffer), 2)
        side_val = 1
    else:
        stop_loss = round(price * (1 + sl_buffer), 2)
        take_profit = round(price * (1 - tp_buffer), 2)
        side_val = -1

    ltp = get_ltp(fyers_symbol)
    if not ltp or abs(ltp - price) > 2.0:
        return

    payload = {
        "symbol": fyers_symbol,
        "qty": qty,
        "type": 1,
        "side": side_val,
        "productType": "INTRADAY",
        "limitPrice": price,
        "stopLoss": stop_loss,
        "takeProfit": take_profit,
        "validity": "DAY",
        "offlineOrder": False
    }

    response = place_order(payload)
    fy_order_id = response.get("id", "")
    status = response.get("s", "error")

    cursor.execute("""
        INSERT INTO orders (alert_id, fy_order_id, order_type, qty, price, sl, tp, status, time_placed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            alert_id, fy_order_id, "LIMIT", qty, price,
            stop_loss, take_profit, status,
            datetime.utcnow().isoformat()
        )
    )
    cursor.execute("UPDATE alerts SET status=? WHERE id=?", (status, alert_id))
    conn.commit()
