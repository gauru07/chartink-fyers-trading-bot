from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from dateutil import parser  # ✅ NEW IMPORT
from fyers_client import place_order, get_ltp, get_candles

# Load .env
load_dotenv()

client_id = os.getenv("CLIENT_ID")
secret_id = os.getenv("SECRET_ID")
redirect_uri = os.getenv("REDIRECT_URI")
# with open("access_token.txt", "r") as f:
#     fyers_access_token = f.read().strip()
access_token = os.getenv("FYERS_ACCESS_TOKEN")
fyers_refresh_token = os.getenv("FYERS_REFRESH_TOKEN")

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
    enable_lockprofit: bool = False

def check_fyers_status():
    try:
        response = fyers.get_profile()
        return response
    except Exception as e:
        return {"status": "error", "details": str(e)}

# ------------------ TEST ROUTES ------------------
@app.get("/ping")
async def ping():
    return {"status": "alive"}

@app.get("/test-candle")
async def test_candle(symbol: str = "NSE:RELIANCE-EQ"):
    candles = get_candles(symbol)
    if not candles:
        return {"symbol": symbol, "candle_count": 0, "sample": "No data"}

    return {
        "symbol":    symbol,
        "candle_count": len(candles),
        "sample": {"first": candles[0], "last": candles[-1]},
    }

@app.get("/ltp")
async def ltp(symbol: str = "NSE:RELIANCE-EQ"):
    return get_ltp(symbol)

@app.get("/status")
async def status():
    return check_fyers_status()

@app.post("/api/chartink-alert")
async def receive_alert(alert: ChartinkAlert):
    data = alert.dict()
    print("🔔 Received raw payload:", data)

    try:
        # Step 1: Extract and sanitize symbol/price
        symbol_raw = (data.get("stocks") or "RELIANCE").split(",")[0].strip()
        price = float((data.get("trigger_prices") or "1000").split(",")[0].strip())
        triggered_at = data.get("triggered_at") or ""
        timestamp = parser.parse(triggered_at) if triggered_at else datetime.utcnow()
        print(f"✅ Parsed: Symbol={symbol_raw}, Price={price}, Time={timestamp.time()}")

        # Step 2: Settings
        capital = float(data.get("capital", 1000))
        buffer_percent = float(data.get("buffer", 0.09))
        risk_percent = float(data.get("risk", 0.01))
        risk_reward = float(data.get("risk_reward", 1.5))
        lot_size = int(data.get("lot_size", 1))
        side = "long"  # TODO: Allow for "short" via payload if needed

        symbol = f"NSE:{symbol_raw.upper()}-EQ"

        candles = get_candles(symbol)
        if not candles or len(candles) < 2:
            raise HTTPException(status_code=400, detail=f"Fyers rejected symbol '{symbol}'. It may not be supported or not enough data.")

        [_, o1, h1, l1, c1, _] = candles[0]
        [_, o2, h2, l2, c2, _] = candles[1]

        if side == "long":
            buffer_val = (h1 - o1) * buffer_percent
            entry_price = h1 + buffer_val
            stoploss = h1
            target = entry_price + (entry_price - stoploss) * risk_reward
        else:
            buffer_val = (o1 - l1) * buffer_percent
            entry_price = l1 - buffer_val
            stoploss = l1
            target = entry_price - (stoploss - entry_price) * risk_reward

        # Position Sizing
        if abs(entry_price - stoploss) < 0.01:
            raise HTTPException(status_code=400, detail="Entry and Stoploss too close or same. Risk too small for a valid trade.")
        risk_per_trade = capital * risk_percent
        qty = max(1, int(risk_per_trade / abs(entry_price - stoploss))) * lot_size

        # Place only one Limit order
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

        # Optionally: Save to positions.json for monitoring
        position_data = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "entry": round(entry_price, 2),
            "stoploss": round(stoploss, 2),
            "target": round(target, 2)
        }
        try:
            import json
            with open("positions.json", "w") as f:
                json.dump([position_data], f, indent=2)
        except Exception as e:
            print("❗ positions.json save failed:", e)

        return {"status": "ok", "order_response": limit_resp, "details": position_data}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
