from fyers_apiv3 import fyersModel
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load access token
# with open("access_token.txt", "r") as f:
#     access_token = f.read().strip()
from dotenv import load_dotenv
load_dotenv()
access_token = os.getenv("FYERS_ACCESS_TOKEN")

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
    if not access_token:
        print("❌ No access token loaded! Check env config.")



# ✅ Get LTP (Last Traded Price)
def get_ltp(symbol: str):
    try:
        response = fyers.quotes({"symbols": symbol})
        return response
    except Exception as e:
        return {"error": str(e)}


def get_candles(symbol: str):
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)  # last 10 min (to get at least 2 candles)

        response = fyers.history({
            "symbol": symbol,
            "resolution": "1",  # 1-minute candle
            "date_format": "1",
            "range_from": start_time.strftime("%Y-%m-%d"),
            "range_to": end_time.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        })

        if response.get("s") != "ok":
            print("⚠️ Fyers History Error:", response)
            return []

        candles = response["candles"]
        print("📊 Requesting candles for:", symbol)
        return candles[-2:]  # return last 2 candles
    except Exception as e:
        print("⚠️ Error fetching candles:", str(e))
        return []

