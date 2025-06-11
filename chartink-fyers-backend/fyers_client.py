from fyers_apiv3 import fyersModel
from dotenv import load_dotenv
import os

load_dotenv()
client_id = os.getenv("FYERS_APP_ID")
access_token = os.getenv("FYERS_ACCESS_TOKEN")

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token)

def get_ltp(symbol):
    try:
        res = fyers.quotes({"symbols": symbol})
        return res['d'][0]['v']['lp']
    except:
        return None

def place_order(payload):
    try:
        return fyers.place_order(payload)
    except Exception as e:
        return {"s": "error", "message": str(e)}
