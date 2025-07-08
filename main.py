from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from fyers_client import get_candles

# You will use your real fyers_client here
from fyers_client import place_order, get_ltp, get_candles

# Load .env
load_dotenv()

client_id = os.getenv("CLIENT_ID")
secret_id = os.getenv("SECRET_ID")
redirect_uri = os.getenv("REDIRECT_URI")
# fyers_access_token = os.getenv("FYERS_ACCESS_TOKEN")
with open("access_token.txt", "r") as f:
    fyers_access_token = f.read().strip()
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

# Define Pydantic model for the expected payload
class ChartinkAlert(BaseModel):
    webhook_url: str = None
    stocks: str = None
    trigger_prices: str = None
    triggered_at: str = None
    type: str = None
    testLogicOnly: bool = False
    capital: float = 100000
    buffer: float = 0.09
    risk: float = 0.01
    risk_reward: float = 1.5
    lot_size: int = 1
    enable_instant: bool = True
    enable_stoplimit: bool = True
    enable_lockprofit: bool = False


@app.get("/ping")
async def ping():
    return {"status": "alive"}

# -----------------  NEW TEST ENDPOINTS  -----------------
@app.get("/test-candle")
async def test_candle(symbol: str = "NSE:RELIANCE-EQ"):
    """
    Quick sanity-check that we can talk to FYERS.

    • pass ?symbol=NSE:TCS-EQ to test other scrips
    • returns candle count and first / last candle received
    """
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
    """
    Lightweight ping to ensure quotes endpoint works.
    """
    return get_ltp(symbol)
# --------------------------------------------------------



@app.post("/api/chartink-alert")
async def receive_alert(alert: ChartinkAlert):
    data = alert.dict()
    print("🔔 Received raw payload:", data)

    # Step 2: Identify if coming from Chartink
    is_chartink = "chartink" in (data.get("webhook_url") or "")

    # Step 3: Extract values with fallback defaults
    try:
        symbol_raw = (data.get("stocks") or "RELIANCE").split(",")[0].strip()
        price = float((data.get("trigger_prices") or "1000").split(",")[0].strip())
        triggered_at = data.get("triggered_at") or ""
        timestamp = datetime.strptime(triggered_at.strip(), "%I:%M %p") if triggered_at else datetime.utcnow()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload structure: {str(e)}")

    print(f"✅ Parsed: Symbol={symbol_raw}, Price={price}, Time={timestamp.time()}")

    # Step 4: Customizable Settings (from payload or default)
    test_logic = data.get("testLogicOnly", False)
    capital = float(data.get("capital", 100000))
    buffer_percent = float(data.get("buffer", 0.09))
    risk_percent = float(data.get("risk", 0.01))
    risk_reward = float(data.get("risk_reward", 1.5))
    lot_size = int(data.get("lot_size", 1))

    enable_instant = data.get("enable_instant", True if is_chartink else False)
    enable_stoplimit = data.get("enable_stoplimit", True if is_chartink else False)
    enable_lockprofit = data.get("enable_lockprofit", False)

    order_type = 2 if (data.get("type") or "Market").lower() == "market" else 1
    side = "long"

    # Step 5: Candle logic
    # symbol = f"NSE:{symbol_raw.upper()}-EQ"
    symbol = f"NSE:{symbol_raw.upper()}"  # remove -EQ

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

    # Risk & Quantity
    risk_per_trade = capital * risk_percent
    qty = max(1, int(risk_per_trade / abs(entry_price - stoploss))) * lot_size

    response = {}

    # Step 6: Market Order
    if enable_instant:
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

    # Step 7: Limit Order
    if enable_stoplimit:
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

    return {"status": "ok", "details": response}
