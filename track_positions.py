import time
import json
import os
from datetime import datetime
from fyers_client import fyers, get_ltp, place_order, get_orderbook

POSITIONS_FILE = 'positions.json'
LOG_FILE = 'track_positions.log'

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as logf:
        logf.write(f"[{timestamp}] {message}\n")
    print(message)

def get_filled_symbols():
    try:
        order_response = get_orderbook()
        filled = []

        if order_response.get("s") == "ok":
            for order in order_response.get("orderBook", []):
                if order.get("status") == 2:  # 2 = Filled
                    filled.append({
                        "symbol": order["symbol"],
                        "side": "long" if order["side"] == 1 else "short"
                    })
        return filled

    except Exception as e:
        log(f"❌ Failed to fetch orderbook: {e}")
        return []

while True:
    try:
        if not os.path.exists(POSITIONS_FILE):
            log("⚠️ positions.json not found. Waiting...")
            time.sleep(5)
            continue

        try:
            with open(POSITIONS_FILE, 'r') as f:
                positions = json.load(f)
        except json.JSONDecodeError:
            log("⚠️ positions.json is empty or corrupted.")
            time.sleep(5)
            continue

        filled_orders = get_filled_symbols()
        active_positions = []

        for pos in positions:
            is_filled = any(
                p['symbol'] == pos['symbol'] and p['side'] == pos['side']
                for p in filled_orders
            )

            if not is_filled:
                log(f"🟡 Waiting for order fill: {pos['symbol']} ({pos['side']})")
                active_positions.append(pos)
                continue

            ltp_data = get_ltp(pos['symbol'])
            if isinstance(ltp_data, dict) and "d" in ltp_data and len(ltp_data["d"]) > 0:
                ltp = float(ltp_data["d"][0]["v"])
            else:
                log(f"❌ Invalid LTP for {pos['symbol']}: {ltp_data}")
                active_positions.append(pos)
                continue

            log(f"📊 {pos['symbol']} ({pos['side']}): LTP={ltp} | SL={pos['stoploss']}")

            sl_hit = (
                pos['side'] == 'long' and ltp <= pos['stoploss']
            ) or (
                pos['side'] == 'short' and ltp >= pos['stoploss']
            )

            if sl_hit:
                log(f"🚨 SL HIT — Reversing position for {pos['symbol']}")

                new_side = 'short' if pos['side'] == 'long' else 'long'
                fyers_side = -1 if new_side == 'short' else 1

                stop_trigger = pos['stoploss']
                buffer = 0.1
                entry_price = stop_trigger - buffer if new_side == 'short' else stop_trigger + buffer

                rr = 1.5
                sl_diff = abs(entry_price - stop_trigger)
                new_target = entry_price + (rr * sl_diff) if new_side == 'long' else entry_price - (rr * sl_diff)
                new_sl = stop_trigger

                stop_limit_order = {
                    "symbol": pos['symbol'],
                    "qty": pos['qty'],
                    "side": fyers_side,
                    "type": 3,  # Stop Limit
                    "limitPrice": round(entry_price, 2),
                    "stopPrice": round(stop_trigger, 2),
                    "takeProfit": round(new_target, 2),
                    "stopLoss": round(new_sl, 2),
                    "productType": "INTRADAY",
                    "validity": "DAY",
                    "offlineOrder": False
                }

                log(f"📤 Placing Reversal Order: {stop_limit_order}")
                place_order(stop_limit_order)

                active_positions.append({
                    "symbol": pos['symbol'],
                    "side": new_side,
                    "qty": pos['qty'],
                    "stoploss": new_sl
                })

            else:
                active_positions.append(pos)

        with open(POSITIONS_FILE, 'w') as f:
            json.dump(active_positions, f, indent=2)

    except Exception as e:
        log(f"❌ Monitor Error: {e}")

    time.sleep(10)
