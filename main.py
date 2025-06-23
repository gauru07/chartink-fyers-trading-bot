from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fyers_client import place_order, get_candles
from datetime import datetime
from typing import Optional

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1️⃣ Define a model matching Chartink's payload
class ChartinkPayload(BaseModel):
    stocks: str
    trigger_prices: str
    triggered_at: str
    scan_name: Optional[str]
    scan_url: Optional[str]
    alert_name: Optional[str]
    webhook_url: Optional[str]

@app.post("/api/chartink-alert")
async def receive_alert(alert: ChartinkPayload, req: Request):
    # 2️⃣ Log raw JSON and Pydantic model
    body = await req.json()
    print("🔔 Received raw payload:", body)
    print("✅ Parsed model:", alert)

    # 3️⃣ Extract first stock and price
    symbol_raw = alert.stocks.split(",")[0].strip()
    price = float(alert.trigger_prices.split(",")[0].strip())

    # 4️⃣ Parse timestamp (if needed)
    try:
        timestamp = datetime.strptime(alert.triggered_at.strip(), "%I:%M %p")
    except:
        timestamp = datetime.utcnow()
    print(f"→ Symbol: {symbol_raw}, Price: {price}, Time: {timestamp.time()}")

    # 5️⃣ Your existing trading logic
    symbol = f"NSE:{symbol_raw.upper()}-EQ"
    candles = get_candles(symbol)
    if len(candles) < 2:
        raise HTTPException(status_code=400, detail="Not enough candles")

    [_, o1, h1, l1, c1, _] = candles[0]
    [_, o2, h2, l2, c2, _] = candles[1]

    # (… your entry/exit calculations based on existing logic …)
    # Example for a long position:
    buffer_val = (h1 - o1) * 0.09
    entry_price = h1 + buffer_val
    stoploss = h1
    target = entry_price + (entry_price - stoploss) * 1.5
    risk_per_trade = 100000 * 0.01
    qty = max(1, int(risk_per_trade / abs(entry_price - stoploss)))

    market_payload = {
        "symbol": symbol,
        "qty": qty,
        "side": 1,
        "type": 2,
        "productType": "INTRADAY",
        "validity": "DAY",
        "offlineOrder": False,
        "stopLoss": round(stoploss, 2),
        "takeProfit": round(target, 2),
    }
    resp = place_order(market_payload)

    return {
        "status": "success",
        "symbol": symbol_raw,
        "price": price,
        "entry": round(entry_price, 2),
        "sl": round(stoploss, 2),
        "tp": round(target, 2),
        "qty": qty,
        "order_response": resp,
    }
