import json
import requests
import pyotp
import sys
from urllib.parse import urlparse, parse_qs
from fyers_apiv3 import fyersModel
import credentials as cr
import os

# Configuration
APP_ID = cr.APP_ID
APP_TYPE = cr.APP_TYPE
SECRET_KEY = cr.SECRET_KEY
FY_ID = cr.FY_ID
APP_ID_TYPE = cr.APP_ID_TYPE
TOTP_KEY = cr.TOTP_KEY
PIN = cr.PIN
REDIRECT_URI = cr.REDIRECT_URI
CLIENT_ID = f'{APP_ID}-{APP_TYPE}'

# API endpoints
BASE_URL = "https://api-t2.fyers.in/vagator/v2"
BASE_URL_2 = "https://api-t1.fyers.in/api/v3"
URL_SEND_LOGIN_OTP = BASE_URL + "/send_login_otp"
URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
URL_VERIFY_PIN = BASE_URL + "/verify_pin"
URL_TOKEN = BASE_URL_2 + "/token"

SUCCESS = 1
ERROR = -1

# ——— Utility Functions ——— #
def send_login_otp(fy_id, app_id):
    res = requests.post(URL_SEND_LOGIN_OTP, json={"fy_id": fy_id, "app_id": app_id})
    if res.status_code != 200:
        return [ERROR, res.text]
    return [SUCCESS, res.json()["request_key"]]

def verify_totp(request_key, totp):
    res = requests.post(URL_VERIFY_TOTP, json={"request_key": request_key, "otp": totp})
    if res.status_code != 200:
        return [ERROR, res.text]
    return [SUCCESS, res.json()["request_key"]]

def generate_totp(secret):
    return pyotp.TOTP(secret).now()

def verify_pin(request_key, pin):
    payload = {"request_key": request_key, "identity_type": "pin", "identifier": pin}
    res = requests.post(URL_VERIFY_PIN, json=payload)
    print(res.json())
    if res.status_code != 200:
        return [ERROR, res.text]
    return [SUCCESS, res.json()["data"]["access_token"]]

def get_auth_code(fy_id, app_id, redirect_uri, app_type, access_token):
    payload = {
        "fyers_id": fy_id,
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "appType": app_type,
        "code_challenge": "",
        "state": "sample_state",
        "scope": "",
        "nonce": "",
        "response_type": "code",
        "create_cookie": True
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.post(URL_TOKEN, json=payload, headers=headers)
    if res.status_code != 200 and res.status_code != 308:
        return [ERROR, f"/token failed: {res.text}"]

    res_json = res.json()
    auth_code = res_json.get("data", {}).get("auth")
    if not auth_code and "Url" in res_json:
        parsed = urlparse(res_json["Url"])
        auth_code = parse_qs(parsed.query).get("auth_code", [None])[0]

    if not auth_code:
        return [ERROR, f"auth_code not found in response: {json.dumps(res_json)}"]

    return [SUCCESS, auth_code]

def update_env_var(key, value, env_path=".env"):
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"{key}={value}\n")
        return

    with open(env_path, "r") as f:
        lines = f.readlines()
    with open(env_path, "w") as f:
        found = False
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={value}\n")


# ——— Main Flow ——— #
def main():
    print(f"\n🌐 Activate manually (optional): https://api-t1.fyers.in/api/v3/generate-authcode?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=None\n")

    print("🔐 Sending login OTP...")
    send_otp = send_login_otp(FY_ID, APP_ID_TYPE)
    if send_otp[0] != SUCCESS:
        print(f"❌ Failed to send OTP: {send_otp[1]}")
        sys.exit()

    print("⏱️ Generating TOTP...")
    totp = generate_totp(TOTP_KEY)
    print(f"✅ TOTP: {totp}")

    print("🔐 Verifying TOTP...")
    verify_otp = verify_totp(send_otp[1], totp)
    if verify_otp[0] != SUCCESS:
        print(f"❌ Failed to verify TOTP: {verify_otp[1]}")
        sys.exit()

    print("🔓 Verifying PIN...")
    pin_response = verify_pin(verify_otp[1], PIN)
    if pin_response[0] != SUCCESS:
        print(f"❌ PIN verification failed: {pin_response[1]}")
        sys.exit()

    print("🔑 Fetching Auth Code...")
    token_response = get_auth_code(FY_ID, APP_ID, REDIRECT_URI, APP_TYPE, pin_response[1])
    if token_response[0] != SUCCESS:
        print(f"❌ Auth Code Fetch Failed: {token_response[1]}")
        sys.exit()

    print("✅ Auth Code:", token_response[1])

    # Final Step - Generate Access Token
    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    session.set_token(token_response[1])
    response = session.generate_token()

    if response["s"].lower() == "ok":
        final_access_token = response["access_token"]
        print("🔐 Final Access Token:", final_access_token)

        # Save to .txt
        with open("access_token.txt", "w") as f:
            f.write(final_access_token)
        print("✅ Access token saved to access_token.txt")

        # Update to .env
        update_env_var("FYERS_ACCESS_TOKEN", final_access_token)
        print("✅ Access token saved to .env file (FYERS_ACCESS_TOKEN)")

    else:
        print("❌ Failed to generate access token:")
        print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
