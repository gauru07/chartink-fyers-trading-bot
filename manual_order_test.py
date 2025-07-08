from fyers_apiv3 import fyersModel
import os

# Load access token from file
with open("access_token.txt", "r") as f:
    access_token = f.read().strip()

client_id = "I2YG2SAKG1-100"  # Your actual client ID

# Create fyers object
fyers = fyersModel.FyersModel(
    client_id=client_id,
    token=access_token,
    is_async=False,
    log_path=""
)

# ----------- PLACE DUMMY ORDER (Market Buy TATAMOTORS) -----------
order_payload = {
    "symbol": "NSE:TATAMOTORS-EQ",
    "qty": 1,
    "side": 1,  # 1 = Buy, -1 = Sell
    "type": 2,  # 2 = Market Order
    "productType": "INTRADAY",
    "limitPrice": 0,
    "stopLoss": 0,
    "takeProfit": 0,
    "validity": "DAY",
    "offlineOrder": False
}

response = fyers.place_order(order_payload)
print("🔔 Order Response:")
print(response)
