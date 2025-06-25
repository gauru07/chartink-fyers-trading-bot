import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import time
import schedule
import json

# Your deployed backend endpoint
BACKEND_URL = "https://yourbackendurl.com/api/chartink-alert"

def fetch_and_trade():
    print("📡 Fetching Chartink scan...")

    url = "https://chartink.com/screener/process"
    condition = {"scan_clause" : "( {cash} ( latest rsi( 14 ) >= 70 ) ) "}

    with requests.session() as s:
        r_data = s.get(url)
        soup = bs(r_data.content, "html.parser")
        meta = soup.find("meta", {"name": "csrf-token"})["content"]
        header = {"x-csrf-token": meta}

        response = s.post(url, headers=header, data=condition)
        data = response.json()

        df = pd.DataFrame(data["data"])
        print(df)

        if df.empty:
            print("⚠️ No stocks found this cycle.")
            return

        for _, row in df.iterrows():
            payload = {
                "testLogicOnly": False,
                "stocks": row["nsecode"],
                "trigger_prices": str(row["close"]),
                "type": "Market",  # or "Limit"
                "capital": 100000,
                "buffer": 0.1,
                "risk": 0.1,
                "risk_reward": 1.5,
                "lot_size": 1,
                "enable_instant": True,
                "enable_stoplimit": True,
                "enable_lockprofit": False,
                "triggered_at": time.strftime("%I:%M %p")
            }

            try:
                resp = requests.post(BACKEND_URL, json=payload)
                print(f"✅ Order sent for {row['nsecode']} | Response: {resp.status_code}")
            except Exception as e:
                print(f"❌ Error placing order for {row['nsecode']}: {e}")

# Schedule every 5 min
schedule.every(5).minutes.do(fetch_and_trade)

print("🚀 Starting 5-minute scanner loop...\n")
fetch_and_trade()  # run once initially

while True:
    schedule.run_pending()
    time.sleep(1)
