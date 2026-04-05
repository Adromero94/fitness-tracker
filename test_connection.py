import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "fitness-tracker-492416-dcbba21febe5.json", scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key("1k9nFX81yM1PaEfyRqho-DXgKzJ1lxbRWohKZkobFQUU").sheet1

print("✅ Connected successfully!")
print(f"Sheet title: {sheet.spreadsheet.title}")
