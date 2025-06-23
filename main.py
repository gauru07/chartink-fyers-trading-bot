from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fyers_client import place_order, get_ltp, get_candles
from datetime import datetime
from typing import Optional

app = FastAPI()

# ✅ CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://chartink-fyers-trading-bot-frontend.onrender.com",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Chartink Alert Handler
@app.post("/api/chartink-alert")
async def receive_alert(req: Request):
    # 🔍 Step 1: Log raw incoming JSON
    data = await req.json()
    print("🔔 Received raw payload:", data)

    # 🧠 Step 2: Parse values
    try:
        symbol_raw = data["stocks"].split(",")[0].strip()
        price = float(data["trigger_prices"].split(",")[0].strip())
        triggered_at = data.get("triggered_at", "")
        timestamp = datetime.strptime(triggered_at.strip(), "%I:%M %p") if triggered_at else datetime.utcnow()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload structure: {str(e)}")

    print(f"✅ Parsed: Symbol={symbol_raw}, Price={price}, Time={timestamp.time()}")

    # 🎯 Step 3: Trading parameters (use constants or future enhancements)
    capital = 100000
    buffer_percent = 0.09
    risk_reward = 1.5
    order_type = 2  # 1 = Limit, 2 = Market
    side = "long"   # or "short"
    enable_instant = True
    enable_stoplimit = True

    # 🔎 Step 4: Candle fetch and entry/exit logic
    symbol = f"NSE:{symbol_raw.upper()}-EQ"
    candles = get_candles(symbol)

    if len(candles) < 2:
        raise HTTPException(status_code=400, detail="Not enough candle data")

    [_, o1, h1, l1, c1, _] = candles[0]
    [_, o2, h2, l2, c2, _] = candles[1]

    if side == "long":
        buffer_val = (h1 - o1) * buffer_percent
        entry_price = h1 + buffer_val
        stoploss = h1 if order_type == 2 else c2
        target = entry_price + (entry_price - stoploss) * risk_reward
    else:
        buffer_val = (o1 - l1) * buffer_percent
        entry_price = l1 - buffer_val
        stoploss = l1 if order_type == 2 else c2
        target = entry_price - (stoploss - entry_price) * risk_reward

    # 💰 Step 5: Risk management
    risk_per_trade = capital * 0.01
    qty = max(1, int(risk_per_trade / abs(entry_price - stoploss)))

    response = {}

# ✅ Step 6: Conditionally place Market Order
if data.get("enable_instant", False):
    market_payload = {
        "symbol": symbol,
        "qty": qty,
        "side": 1 if side == "long" else -1,
        "type": 2,  # Market
        "productType": "INTRADAY",
        "validity": "DAY",
        "offlineOrder": False,
        "stopLoss": round(stoploss, 2),
        "takeProfit": round(target, 2)
    }
    market_resp = place_order(market_payload)
    print("✅ Market Order Placed:", market_payload)
    response["market_order"] = market_resp

# ✅ Step 7: Conditionally place Limit Order
if data.get("enable_stoplimit", False):
    limit_payload = {
        "symbol": symbol,
        "qty": qty,
        "side": 1 if side == "long" else -1,
        "type": 1,  # Limit
        "productType": "INTRADAY",
        "validity": "DAY",
        "offlineOrder": False,
        "limitPrice": round(entry_price, 2),
        "stopLoss": round(stoploss, 2),
        "takeProfit": round(target, 2)
    }
    limit_resp = place_order(limit_payload)
    print("✅ Limit Order Placed:", limit_payload)
    response["limit_order"] = limit_resp
