from fyers_client import place_order

payload = {
    "symbol": "NSE:TATAMOTORS",
    "qty": 1,
    "side": 1,
    "type": 2,
    "productType": "INTRADAY",
    "validity": "DAY",
    "offlineOrder": False,
    "stopLoss": 650,
    "takeProfit": 720
}

response = place_order(payload)
print(response)
