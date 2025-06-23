from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fyers_client import place_order, get_candles
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

@app.post("/api/chartink-alert")
async def receive_alert(req: Request):
    data = await req.json()
    print("\U0001F514 Received raw payload:", data)

    try:
        # Parse core fields
        stocks = data.get("stocks", "").split(",")
        trigger_prices = data.get("trigger_prices", "").split(",")
        triggered_at = data.get("triggered_at", "")
        timestamp = datetime.strptime(triggered_at.strip(), "%I:%M %p") if triggered_at else datetime.utcnow()

        # Use first stock and price for this order logic
        symbol_raw = stocks[0].strip()
        price = float(trigger_prices[0].strip())

        print(f"✅ Parsed: Symbol={symbol_raw}, Price={price}, Time={timestamp.time()}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")

    # Extract config values
    capital = float(data.get("capital", 100000))
    buffer_percent = float(data.get("buffer", 0.09))
    fixed_buffer = float(data.get("fixed_buffer", 0))  # optional
    risk_reward = float(data.get("risk_reward", 1.5))
    test_mode = data.get("test_mode", False)
    enable_instant = data.get("enable_instant", False)
    enable_stoplimit = data.get("enable_stoplimit", False)
    enable_lockprofit = data.get("enable_lockprofit", False)

    side = "long"  # hardcoded for now
    order_type = data.get("type", 2)  # 2 = Market, 1 = Limit

    symbol = f"NSE:{symbol_raw.upper()}-EQ"

    # In test logic mode, use dummy candle
    if test_mode:
        entry_price = price + 0.45
        stoploss = price
        target = entry_price + (entry_price - stoploss) * risk_reward
    else:
        candles = get_candles(symbol)
        if len(candles) < 2:
            raise HTTPException(status_code=400, detail="Not enough candle data")

        [_, o1, h1, l1, c1, _] = candles[0]
        [_, o2, h2, l2, c2, _] = candles[1]

        if side == "long":
            buffer_val = (h1 - o1) * buffer_percent + fixed_buffer
            entry_price = h1 + buffer_val
            stoploss = h1 if order_type == 2 else c2
            target = entry_price + (entry_price - stoploss) * risk_reward
        else:
            buffer_val = (o1 - l1) * buffer_percent + fixed_buffer
            entry_price = l1 - buffer_val
            stoploss = l1 if order_type == 2 else c2
            target = entry_price - (stoploss - entry_price) * risk_reward

    # Quantity calc (risk mgmt)
    risk_per_trade = capital * 0.01
    qty = max(1, int(risk_per_trade / abs(entry_price - stoploss)))

    response = {}

    if enable_instant:
        market_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if side == "long" else -1,
            "type": 2,
            "productType": "INTRADAY",
            "validity": "DAY",
            "offlineOrder": False,
            "stopLoss": round(stoploss, 2),
            "takeProfit": round(target, 2)
        }
        market_resp = place_order(market_payload)
        print("✅ Market Order Placed:", market_payload)
        response["market_order"] = market_resp

    if enable_stoplimit:
        limit_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if side == "long" else -1,
            "type": 1,
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

    if enable_lockprofit:
        # 🚧 Optional logic for future lock-profit implementation
        print("🔒 Lock Profit flag is enabled — logic not yet implemented.")

    return {"status": "success", "details": response}
