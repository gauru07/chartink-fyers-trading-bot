import os
import requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("CLIENT_ID")
secret_id = os.getenv("SECRET_ID")
refresh_token = os.getenv("FYERS_REFRESH_TOKEN")
redirect_uri = os.getenv("REDIRECT_URI")

url = "https://api.fyers.in/api/v3/token"
payload = {
    "grant_type": "refresh_token",
    "client_id": client_id,
    "secret_key": secret_id,
    "refresh_token": refresh_token,
    "redirect_uri": redirect_uri
}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

response = requests.post(url, data=payload, headers=headers)
print(response.status_code)
print(response.json())
