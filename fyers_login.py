from fyers_apiv2 import accessToken
import webbrowser

client_id = "I2YG2SAKG1-100"
secret_key = "MZLR6H0ASH"
redirect_uri = "https://127.0.0.1"
response_type = "code"
state = "sample_state"

session = accessToken.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type=response_type,
    state=state
)

# Step 1: Get auth URL and visit
auth_url = session.generate_authcode()
print("🔗 Visit this URL and login:", auth_url)
webbrowser.open(auth_url)
