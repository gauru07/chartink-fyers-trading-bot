from fyers_apiv3 import fyersModel
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv


with open("access_token.txt", "r") as f:
            token = f.read().strip()
            print("DEBUG: Loaded token from access_token.txt:", token[:16], "...", "length:", len(token))

client_id = "I2YG2SAKG1-100"
fyers = fyersModel.FyersModel(client_id=client_id, token=token, is_async=False)

def place_order(order_payload):
    print("📦 Sending order to Fyers:", order_payload)
    try:
        response = fyers.place_order(order_payload)
        print("📩 Response from Fyers:", response)
        return response
    except Exception as e:
        print("❌ Fyers order error:", str(e))
        return {"error": str(e)}
    if not access_token:
        print("❌ No access token loaded! Check env config.")



# ✅ Get LTP (Last Traded Price)
def get_ltp(symbol: str):
    try:
        response = fyers.quotes({"symbols": symbol})
        return response
    except Exception as e:
        return {"error": str(e)}


profile = fyers.get_profile()
print("DEBUG: Fyers get_profile response:", profile)

def get_candles(symbol):
    now = datetime.now()
    start_unix = int((now - timedelta(minutes=5)).timestamp())
    end_unix = int(now.timestamp())

    data = {
        "symbol": symbol,  # use NSE:SBIN-EQ here
        "resolution": "1",
        "date_format": "0",   # use UNIX format
        "range_from": str(start_unix),
        "range_to": str(end_unix),
        "cont_flag": "1"
    }

    try:
        response = fyers.history(data)
        print("🧪 SDK candle response:", response)
        if response.get("s") == "ok":
            return response.get("candles", [])
        else:
            print("❌ Fyers SDK error:", response)
            return []
    except Exception as e:
        print("❌ Candle Fetch Error:", e)
        return []
