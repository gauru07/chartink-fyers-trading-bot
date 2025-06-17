from datetime import datetime

# Dummy order function – replace with FYERS SDK/API call
def place_order(order_payload: dict):
    print("ORDER PLACED:", order_payload)
    return {
        "s": "ok",
        "id": f"ORD-{int(datetime.now().timestamp())}"
    }

# Dummy latest price – can be improved to fetch LTP
def get_ltp(symbol: str):
    return 735.0  # Placeholder value

# Dummy 5-minute candle data – replace with FYERS candle API later
def get_candles(symbol: str):
    return [
        [1718702400, 730, 735, 728, 731, 100000],  # Candle 1
        [1718702700, 731, 736, 730, 735, 105000],  # Candle 2
    ]
