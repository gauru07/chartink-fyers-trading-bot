from fyers_apiv3 import fyersModel
import os
from dotenv import load_dotenv

# Load access token
with open("access_token.txt", "r") as f:
    access_token = f.read().strip()

client_id = "I2YG2SAKG1-100"

fyers = fyersModel.FyersModel(
    client_id=client_id,
    token=access_token,
    is_async=False,
    log_path=""  # Disable logging errors
)

# ✅ Place order
# def place_order(payload: dict):
#     try:
#         response = fyers.place_order(payload)
#         return response
#     except Exception as e:
#         return {"error": str(e)}
    
def place_order(order_payload):
    print("📦 Sending order to Fyers:", order_payload)
    try:
        response = fyers.place_order(order_payload)
        print("📩 Response from Fyers:", response)
        return response
    except Exception as e:
        print("❌ Fyers order error:", str(e))
        return {"error": str(e)}


# ✅ Get LTP (Last Traded Price)
def get_ltp(symbol: str):
    try:
        response = fyers.quotes({"symbols": symbol})
        return response
    except Exception as e:
        return {"error": str(e)}

# ✅ Get Candle Data using OHLC from Depth API
def get_candles(symbol: str):
    try:
        response = fyers.depth({"symbol": symbol, "ohlcv_flag": "1"})
        if response.get("s") != "ok":
            return []

        candle = response["d"].get(symbol, {})
        return [[
            "",  # No timestamp
            candle.get("o"),  # open
            candle.get("h"),  # high
            candle.get("l"),  # low
            candle.get("c"),  # close
            candle.get("v")   # volume
        ]]
    except Exception as e:
        print("⚠️ Error fetching candle:", e)
        return []
