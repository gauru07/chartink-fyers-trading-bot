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
        start_time = end_time - timedelta(minutes=10)

        # Try with original symbol
        response = fyers.history({
            "symbol": symbol,
            "resolution": "1",
            "date_format": "1",
            "range_from": start_time.strftime("%Y-%m-%d"),
            "range_to": end_time.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        })

        if response.get("s") == "ok":
            return response["candles"][-2:]

        # Try fallback: add or remove -EQ and retry
        if "-EQ" in symbol:
            fallback_symbol = symbol.replace("-EQ", "")
        else:
            fallback_symbol = symbol + "-EQ"

        response2 = fyers.history({
            "symbol": fallback_symbol,
            "resolution": "1",
            "date_format": "1",
            "range_from": start_time.strftime("%Y-%m-%d"),
            "range_to": end_time.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        })

        if response2.get("s") == "ok":
            return response2["candles"][-2:]

        print("⚠️ Fyers History Error (Both attempts failed):", response2)
        return []
        # Inside get_candles
        if response2.get("s") == "ok":
            print(f"✅ Fallback Symbol Worked: {fallback_symbol}")
            return response2["candles"][-2:]


    except Exception as e:
        print("⚠️ Candle Fetch Error:", str(e))
        return []

# Inside get_candles

