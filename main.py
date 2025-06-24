# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from pymongo import MongoClient
import logging
import os

# -------- LOGGING SETUP --------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------- FASTAPI APP --------
app = FastAPI()

# -------- CORS MIDDLEWARE --------
origins = [
    "https://chartink-fyers-trading-bot-frontend.onrender.com",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- PRE-FLIGHT HANDLER (CORS FIX) --------
@app.options("/api/chartink-alert")
async def preflight_chartink_alert(request: Request):
    return JSONResponse(status_code=200, content={"message": "Preflight OK"})

# -------- ROOT ROUTE --------
@app.get("/")
def read_root():
    return {"message": "Backend is running"}

# -------- MONGODB CONNECTION --------
# MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
# client = MongoClient(MONGO_URL)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017").strip()
client = MongoClient(MONGO_URL)

db = client["order"]
orders_collection = db["orders"]

# -------- SCHEMA --------
class AlertRequest(BaseModel):
    testLogicOnly: Optional[bool] = False
    stocks: Optional[str] = "TESTSTOCK"
    trigger_prices: Optional[str] = "100.5"
    type: Optional[str] = "Market"
    capital: float
    buffer: float
    risk: float
    risk_reward: float
    lot_size: float
    enable_instant: Optional[bool] = False
    enable_stoplimit: Optional[bool] = False
    enable_lockprofit: Optional[bool] = False
    triggered_at: str

# -------- POST ROUTE --------
@app.post("/api/chartink-alert")
def chartink_alert(alert: AlertRequest):
    logger.info("Received alert: %s", alert.dict())

    if alert.testLogicOnly:
        logger.info("[TEST MODE] Simulating logic without placing real orders.")
        order_data = alert.dict()
        order_data["status"] = "test_mode"
        result = orders_collection.insert_one(order_data)
        return {
            "status": "ok",
            "message": "Test order logic simulated.",
            "order_id": str(result.inserted_id)
        }

    # Live order logic
    if alert.enable_instant:
        logger.info("Placing INSTANT MARKET ORDER for %s", alert.stocks)
        order_type = "MARKET"
    elif alert.enable_stoplimit:
        logger.info("Placing STOP LIMIT ORDER for %s", alert.stocks)
        order_type = "STOPLIMIT"
    else:
        logger.info("No order placed. Both instant and stoplimit were disabled.")
        return {"status": "skipped", "message": "No order placed due to disabled flags."}

    order_data = alert.dict()
    order_data["status"] = "live"
    order_data["order_type"] = order_type
    result = orders_collection.insert_one(order_data)

    return {
        "status": "ok",
        "message": "Order logged successfully",
        "order_id": str(result.inserted_id)
    }
