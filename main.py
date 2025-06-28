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


# 🧠 Structure-based SL/TP Logic
def calculate_trade_details(trigger_price: float, rr: float, side: str, prev_candle: dict):
    if side == "long":
        sl = prev_candle["low"]
        tp = trigger_price + (trigger_price - sl) * rr
    else:
        sl = prev_candle["high"]
        tp = trigger_price - (sl - trigger_price) * rr
    return round(sl, 2), round(tp, 2)


# ✅ Chartink Alert Handler
@app.post("/api/chartink-alert")
async def receive_alert(req: Request):
    data = await req.json()
    print("🔔 Received raw payload:", data)

    is_chartink = "chartink" in data.get("webhook_url", "")
    
    try:
        symbol_raw = data.get("stocks", "RELIANCE").split(",")[0].strip()
        price = float(data.get("trigger_prices", "1000").split(",")[0].strip())
        triggered_at = data.get("triggered_at", "")
        timestamp = datetime.strptime(triggered_at.strip(), "%I:%M %p") if triggered_at else datetime.utcnow()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload structure: {str(e)}")

    print(f"✅ Parsed: Symbol={symbol_raw}, Price={price}, Time={timestamp.time()}")

    test_logic = data.get("testLogicOnly", False)
    capital = float(data.get("capital", 100000))
    buffer_percent = float(data.get("buffer", 0.09))
    risk_percent = float(data.get("risk", 0.01))
    risk_reward = float(data.get("risk_reward", 1.5))
    lot_size = int(data.get("lot_size", 1))

    enable_instant = data.get("enable_instant", True if is_chartink else False)
    enable_stoplimit = data.get("enable_stoplimit", True if is_chartink else False)
    enable_lockprofit = data.get("enable_lockprofit", False)

    order_type = 2 if data.get("type", "Market").lower() == "market" else 1
    side = data.get("side", "long")  # "long" or "short"

    # 🕯️ Candle data
    symbol = f"NSE:{symbol_raw.upper()}-EQ"
    candles = get_candles(symbol)

    if len(candles) < 2:
        raise HTTPException(status_code=400, detail="Not enough candle data")

    [_, o1, h1, l1, c1, _] = candles[0]
    [_, o2, h2, l2, c2, _] = candles[1]

    prev_candle = {"open": o1, "high": h1, "low": l1, "close": c1}

    buffer_val = (h1 - l1) * buffer_percent
    entry_price = price + buffer_val if side == "long" else price - buffer_val

    stoploss, target = calculate_trade_details(entry_price, risk_reward, side, prev_candle)

    # 📊 Risk & Quantity
    risk_per_trade = capital * risk_percent
    qty = max(1, int(risk_per_trade / abs(entry_price - stoploss))) * lot_size

    response = {}

    # 🚀 Market Order
    if enable_instant:
        market_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if side == "long" else -1,
            "type": 2,
            "productType": "INTRADAY",
            "validity": "DAY",
            "offlineOrder": False,
            "stopLoss": stoploss,
            "takeProfit": target
        }
        market_resp = place_order(market_payload)
        print("✅ Market Order Placed:", market_payload)
        response["market_order"] = market_resp

    # 💼 Limit Order
    if enable_stoplimit:
        limit_price = round(entry_price, 2)
        limit_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if side == "long" else -1,
            "type": 1,
            "productType": "INTRADAY",
            "validity": "DAY",
            "offlineOrder": False,
            "limitPrice": limit_price,
            "stopLoss": stoploss,
            "takeProfit": target
        }
        limit_resp = place_order(limit_payload)
        print("✅ Limit Order Placed:", limit_payload)
        response["limit_order"] = limit_resp

    return {"status": "ok", "details": response}
