import time
import json
import os
from fyers_client import get_ltp, place_order

POSITIONS_FILE = 'positions.json'

while True:
    try:
        # Skip if positions file doesn't exist yet
        if not os.path.exists(POSITIONS_FILE):
            time.sleep(5)
            continue

        # Load tracked positions
        with open(POSITIONS_FILE, 'r') as f:
            positions = json.load(f)

        remaining = []

        for pos in positions:
            # Get LTP
            ltp = get_ltp(pos['symbol'])
            print(f"LTP for {pos['symbol']} = {ltp}")

            # Check if SL is hit
            sl_hit = (
                pos['side'] == 'long' and ltp <= pos['stoploss']
            ) or (
                pos['side'] == 'short' and ltp >= pos['stoploss']
            )

            if sl_hit:
                print(f"🔁 SL hit for {pos['symbol']} — Reversing Position")

                # Reverse side
                new_side = 'short' if pos['side'] == 'long' else 'long'
                fyers_side = -1 if new_side == 'short' else 1

                # Stop Limit Order parameters
                buffer = 0.1
                stop_trigger = pos['stoploss']
                entry_price = (
                    stop_trigger - buffer if new_side == 'short' else stop_trigger + buffer
                )

                # New target and stoploss
                rr = 1.5
                sl_diff = abs(entry_price - stop_trigger)
                new_target = (
                    entry_price + (rr * sl_diff) if new_side == 'long' else entry_price - (rr * sl_diff)
                )
                new_sl = stop_trigger

                # Stop Limit Order payload
                stop_limit_order = {
                    "symbol": pos['symbol'],
                    "qty": pos['qty'],
                    "side": fyers_side,
                    "type": 3,  # Stop Limit Order
                    "stopPrice": round(stop_trigger, 2),
                    "limitPrice": round(entry_price, 2),
                    "takeProfit": round(new_target, 2),
                    "stopLoss": round(new_sl, 2),
                    "productType": "INTRADAY",
                    "validity": "DAY",
                    "offlineOrder": False
                }

                print("📤 Placing Stop Limit Order (Reversal):", stop_limit_order)
                place_order(stop_limit_order)

            else:
                # Still active, retain in positions file
                remaining.append(pos)

        # Save back remaining (active) positions
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(remaining, f, indent=2)

    except Exception as e:
        print("❌ Monitor Error:", e)

    time.sleep(10)
