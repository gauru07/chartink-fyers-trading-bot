from fyers_apiv3 import fyersModel
import os

client_id = "I2YG2SAKG1-100"
secret_key = "ZVR224RPFB"
redirect_uri = "https://127.0.0.1/callback"
grant_type = "authorization_code"

auth_code = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJJMllHMlNBS0cxIiwidXVpZCI6IjA4ZWNiNTFkYmZhMzRhYjE5NDZkYWQ2MjYzOGI0NjM4IiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IlhEMjIyOTAiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJjYjA0YWJiODgzZGU1NzIxZTgwNDMyYzk3MzVjMzI3ZWQzNmFmNzRmMzc4NGJkZDJhOTg5ODgyZCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImF1ZCI6IltcImQ6MVwiLFwiZDoyXCIsXCJ4OjBcIixcIng6MVwiLFwieDoyXCJdIiwiZXhwIjoxNzUxMzc1MzcwLCJpYXQiOjE3NTEzNDUzNzAsImlzcyI6ImFwaS5sb2dpbi5meWVycy5pbiIsIm5iZiI6MTc1MTM0NTM3MCwic3ViIjoiYXV0aF9jb2RlIn0.N6VQtdntnnkNInCjm48LWwmKVROEqB11nGSFkLuAZZY"

session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    grant_type=grant_type
)

print(session.generate_authcode())

session.set_token(auth_code)
token_response = session.generate_token()

print("✅ TOKEN RESPONSE:")
print(token_response)
