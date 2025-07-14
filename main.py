from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from dateutil import parser
from fyers_client import place_order, get_ltp, get_candles

# Load .env
load_dotenv()

client_id = os.getenv("CLIENT_ID")
access_token = os.getenv("FYERS_ACCESS_TOKEN")

app = FastAPI()

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

# ------------------ PAYLOAD MODEL ------------------
class ChartinkAlert(BaseModel):
    webhook_url: str = None
    stocks: str = None
    trigger_prices: str = None
    triggered_at: str = None
    type: str = None
    testLogicOnly: bool = False
    capital: float = 1000
    buffer: float = 0.09
    risk: float = 0.01
    risk_reward: float = 1.5
    lot_size: int = 1
    enable_instant: bool = True
    enable_stoplimit: bool = True
    enable_lockprofit: bool = False  # Optional, future use


# ------------------ API ROUTES ------------------
@app.post("/api/chartink-alert")
async def receive_alert(alert: ChartinkAlert):
    data = alert.dict()
    print("🔔 Received raw payload:", data)

    try:
        symbol_raw = (data.get("stocks") or "RELIANCE").split(",")[0].strip()
        price = float((data.get("trigger_prices") or "1000").split(",")[0].strip())
        timestamp = parser.parse(data.get("triggered_at") or "") if data.get("triggered_at") else datetime.utcnow()
        print(f"✅ Parsed: Symbol={symbol_raw}, Price={price}, Time={timestamp.time()}")

        # Settings from payload
        capital = float(data.get("capital", 1000))
        buffer_percent = float(data.get("buffer", 0.09))
        risk_percent = float(data.get("risk", 0.01))
        risk_reward = float(data.get("risk_reward", 1.5))
        lot_size = int(data.get("lot_size", 1))
        side = "long"  # Default, can enhance later

        symbol = f"NSE:{symbol_raw.upper()}-EQ"
        candles = get_candles(symbol)

        if not candles or len(candles) < 2:
            raise HTTPException(status_code=400, detail=f"Fyers rejected symbol '{symbol}' or insufficient candle data.")

        [_, o1, h1, l1, c1, _] = candles[0]

        buffer_val = (h1 - o1) * buffer_percent
        entry_price = h1 + buffer_val
        stoploss = h1
        target = entry_price + (entry_price - stoploss) * risk_reward

        if abs(entry_price - stoploss) < 0.01:
            raise HTTPException(status_code=400, detail="Entry and Stoploss too close. Trade invalid.")

        risk_per_trade = capital * risk_percent
        qty = max(1, int(risk_per_trade / abs(entry_price - stoploss))) * lot_size

        # ✅ Dynamic Order Type Logic
        if data.get("enable_stoplimit", False):
            order_type = 4  # Stop Limit
        elif (data.get("type") or "").lower() == "market":
            order_type = 2  # Market Order
        else:
            order_type = 1  # Limit Order (default)

        # Payload Construction
        order_payload = {
            "symbol": symbol,
            "qty": qty,
            "side": 1 if side == "long" else -1,
            "type": order_type,
            "productType": "INTRADAY",
            "validity": "DAY",
            "offlineOrder": False,
            "limitPrice": round(entry_price, 2),
            "stopLoss": round(stoploss, 2),
            "takeProfit": round(target, 2)
        }

        if order_type == 2:
            # Market Order doesn't use limitPrice, remove it
            del order_payload["limitPrice"]

        response = place_order(order_payload)
        print(f"✅ Order Placed [{order_type}]:", order_payload)

        # Save to positions.json for monitoring
        position_data = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "entry": round(entry_price, 2),
            "stoploss": round(stoploss, 2),
            "target": round(target, 2)
        }

        import json
        with open("positions.json", "w") as f:
            json.dump([position_data], f, indent=2)

        return {"status": "ok", "order_response": response, "details": position_data}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


# ------------------ SYSTEM TEST ROUTES ------------------
@app.get("/ping")
async def ping():
    return {"status": "alive"}

@app.get("/test-candle")
async def test_candle(symbol: str = "NSE:RELIANCE-EQ"):
    candles = get_candles(symbol)
    if not candles:
        return {"symbol": symbol, "candle_count": 0, "sample": "No data"}

    return {
        "symbol": symbol,
        "candle_count": len(candles),
        "sample": {"first": candles[0], "last": candles[-1]},
    }

@app.get("/ltp")
async def ltp(symbol: str = "NSE:RELIANCE-EQ"):
    return get_ltp(symbol)
