# main.py

from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trading-app")

# FastAPI instance
app = FastAPI()

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["order"]
orders_collection = db["orders"]

# Pydantic schema for request
class ChartinkAlert(BaseModel):
    testLogicOnly: bool
    stocks: str
    trigger_prices: str
    type: Optional[str] = "Market"
    capital: float
    buffer: float
    risk: float
    risk_reward: float
    lot_size: float
    enable_instant: bool = True
    enable_stoplimit: bool = False
    enable_lockprofit: bool = False
    triggered_at: Optional[str] = None

@app.post("/api/chartink-alert")
async def chartink_alert(payload: ChartinkAlert):
    try:
        logger.info("\n==== Incoming Alert ====")
        logger.info(f"Payload: {payload.dict()}")

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Decide which logic to follow
        if payload.testLogicOnly:
            logger.info("🔍 Test logic only mode active")
            order_type = "TEST"
            reason = "Testing logic only. No real trade."

        elif payload.enable_instant:
            order_type = "MARKET"
            reason = "Instant entry enabled"

        elif payload.enable_stoplimit:
            if payload.type.lower() == "limit":
                order_type = "STOPLIMIT"
                reason = "Stop limit enabled and selected"
            else:
                order_type = "SKIPPED"
                reason = "Stop limit enabled but type not 'limit'"

        else:
            order_type = "SKIPPED"
            reason = "No valid execution flag selected"

        # Compose full order object
        order_data = {
            "symbol": payload.stocks,
            "price": payload.trigger_prices,
            "type": payload.type,
            "mode": order_type,
            "reason": reason,
            "capital": payload.capital,
            "buffer": payload.buffer,
            "risk": payload.risk,
            "risk_reward": payload.risk_reward,
            "lot_size": payload.lot_size,
            "enable_instant": payload.enable_instant,
            "enable_stoplimit": payload.enable_stoplimit,
            "enable_lockprofit": payload.enable_lockprofit,
            "test_logic_only": payload.testLogicOnly,
            "timestamp": timestamp,
            "triggered_at": payload.triggered_at or timestamp
        }

        result = orders_collection.insert_one(order_data)

        logger.info(f"✅ Order logged: {order_data['mode']} | {order_data['symbol']} @ {order_data['price']} | Reason: {reason}")

        return {
            "status": "ok",
            "message": "Order logged successfully",
            "order_id": str(result.inserted_id)
        }

    except Exception as e:
        logger.error(f"❌ Error processing alert: {e}")
        return {"error": str(e)}

@app.get("/logs")
async def get_logs():
    logs = []
    for doc in orders_collection.find().sort("_id", -1).limit(50):
        doc["_id"] = str(doc["_id"])
        logs.append(doc)
    return logs
