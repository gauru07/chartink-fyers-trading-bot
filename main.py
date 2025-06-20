from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fyers_client import place_order, get_ltp, get_candles
from datetime import datetime
from typing import Optional

app = FastAPI()

# ✅ CORS fix to allow frontend from Render
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

# ✅ Chartink alert structure
class ChartinkAlert(BaseModel):
    symbol: str
    price: float
    timestamp: str
    alert_id: str
    capital: Optional[float] = 100000
    buffer: Optional[float] = 0.09
    risk_reward: Optional[float] = 1.5
    type: Optional[int] = 2  # 1 = Limit, 2 = Market
    side: Optional[str] = "long"
    enable_instant: Optional[bool] = True
    enable_stoplimit: Optional[bool] = True
    enable_lockprofit: Optional[bool] = False

@app.post("/api/chartink-alert")
def receive_alert(alert: ChartinkAlert):
    symbol = f"NSE:{alert.symbol.upper()}-EQ"
    candles = get_candles(symbol)

    if len(candles) < 2:
        return {"error": "Not enough candles"}

    [_, o1, h1, l1, c1, _] = candles[0]  # First candle
    [_, o2, h2, l2, c2, _] = candles[1]  # Second candle

    if alert.side == "long":
        buffer_val = (h1 - o1) * alert.buffer
        entry_price = h1 + buffer_val
        stoploss = h1 if alert.type == 2 else c2
        target = entry_price + (entry_price - stoploss) * alert.risk_reward
    else:
        buffer_val = (o1 - l1) * alert.buffer
        entry_price = l1 - buffer_val
        stoploss = l1 if alert.type == 2 else c2
        target = entry_price - (stoploss - entry_price) * alert.risk_reward

    risk_per_trade = alert.capital * 0.01
    qty = max(1, int(risk_per_trade / abs(entry_price - stoploss)))

    response = {}

    if alert.enable_instant:
        market_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if alert.side == "long" else -1,
            "type": 2,
            "productType": "INTRADAY",
            "validity": "DAY",
            "offlineOrder": False,
            "stopLoss": round(stoploss, 2),
            "takeProfit": round(target, 2)
        }
        response["market_order"] = place_order(market_payload)

    if alert.enable_stoplimit:
        limit_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if alert.side == "long" else -1,
            "type": 1,
            "productType": "INTRADAY",
            "validity": "DAY",
            "offlineOrder": False,
            "limitPrice": round(entry_price, 2),
            "stopLoss": round(stoploss, 2),
            "takeProfit": round(target, 2)
        }
        response["limit_order"] = place_order(limit_payload)

    response.update({
        "status": "success",
        "entry": round(entry_price, 2),
        "sl": round(stoploss, 2),
        "tp": round(target, 2),
        "qty": qty,
        "time": datetime.utcnow().isoformat()
    })

    return response
