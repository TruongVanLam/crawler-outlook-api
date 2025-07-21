from msal import ConfidentialClientApplication
import requests

# Config từ Azure
CLIENT_ID = "7d1e08ff-dee7-4de5-a304-651c725cfeb7"
CLIENT_SECRET = "5o98Q~jepwbVF1avI6SUHh36CfXrYB9a.Hwz5bxz"
TENANT_ID = "1a806a92-4129-4ead-b0f0-8c4c44c8c11b"

# Người dùng muốn truy cập hộp thư (phải nằm trong tenant)
USER_EMAIL = "trandoan020202@outlook.com"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]

app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)

# Lấy access token
result = app.acquire_token_for_client(scopes=SCOPES)

if "access_token" in result:
    headers = {
        "Authorization": f"Bearer {result['access_token']}"
    }
    
    # Lấy mail của 1 user cụ thể
    endpoint = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages?$top=5"
    res = requests.get(endpoint, headers=headers)
    
    if res.status_code == 200:
        for msg in res.json()["value"]:
            print("Subject:", msg["subject"])
    else:
        print("Lỗi khi lấy mail:", res.status_code, res.text)
else:
    print("Lỗi xác thực:", result.get("error_description"))
