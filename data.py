# data.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import date
import streamlit as st

# ── Google Sheets connection ──────────────────────────────────
SHEET_KEY = "1k9nFX81yM1PaEfyRqho-DXgKzJ1lxbRWohKZkobFQUU"
CREDS_FILE = "fitness-tracker-492416-dcbba21febe5.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# All columns in the daily log sheet
LOG_COLUMNS = [
    "date", "calories_eaten", "calories_burned_exercise",
    "exercise_type", "exercise_minutes", "steps",
    "steps_calories", "total_calories_burned",
    "weight_lbs", "sleep_hours", "sleep_quality",
    "notes", "deficit_surplus", "status"
]

# All columns in the profile sheet
PROFILE_COLUMNS = [
    "name", "age", "gender", "height_inches",
    "start_weight", "goal_weight", "target_date",
    "activity_level", "bmr", "tdee", "daily_calorie_target"
]

@st.cache_resource
def get_client():
    """Connect to Google Sheets — cached so it only connects once."""
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
    return gspread.authorize(creds)

def get_sheets():
    """Get or create the two sheets: Log and Profile."""
    client = get_client()
    spreadsheet = client.open_by_key(SHEET_KEY)

    sheet_names = [s.title for s in spreadsheet.worksheets()]

    # Create Log sheet if it doesn't exist
    if "Log" not in sheet_names:
        log_sheet = spreadsheet.add_worksheet(title="Log", rows=1000, cols=20)
        log_sheet.append_row(LOG_COLUMNS)
    else:
        log_sheet = spreadsheet.worksheet("Log")

    # Create Profile sheet if it doesn't exist
    if "Profile" not in sheet_names:
        profile_sheet = spreadsheet.add_worksheet(title="Profile", rows=10, cols=20)
        profile_sheet.append_row(PROFILE_COLUMNS)
    else:
        profile_sheet = spreadsheet.worksheet("Profile")

    return log_sheet, profile_sheet

@st.cache_data(ttl=30)
def load_log():
    """Load all daily log entries as a DataFrame."""
    log_sheet, _ = get_sheets()
    data = log_sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=LOG_COLUMNS)
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["calories_eaten", "calories_burned_exercise", "exercise_minutes",
                "steps", "steps_calories", "total_calories_burned",
                "weight_lbs", "sleep_hours", "sleep_quality",
                "deficit_surplus"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def save_log_entry(entry: dict):
    """Save or update a daily log entry."""
    log_sheet, _ = get_sheets()
    df = load_log()
    entry_date = str(entry["date"])

    # Check if entry for this date already exists
    existing_dates = df["date"].astype(str).tolist()
    if entry_date in existing_dates:
        # Find the row number (add 2: 1 for header, 1 for 1-based index)
        row_idx = existing_dates.index(entry_date) + 2
        row_data = [str(entry.get(col, "")) for col in LOG_COLUMNS]
        log_sheet.update(f"A{row_idx}", [row_data])
    else:
        row_data = [str(entry.get(col, "")) for col in LOG_COLUMNS]
        log_sheet.append_row(row_data)
    st.cache_data.clear()


@st.cache_data(ttl=30)
def load_profile():
    """Load the user profile."""
    _, profile_sheet = get_sheets()
    data = profile_sheet.get_all_records()
    if not data:
        return None
    profile = data[-1]
    for col in ["age", "height_inches", "start_weight", "goal_weight",
                "bmr", "tdee", "daily_calorie_target"]:
        try:
            profile[col] = float(profile[col])
        except (ValueError, KeyError):
            profile[col] = 0.0
    return profile


def save_profile(profile: dict):
    """Save or update the user profile."""
    _, profile_sheet = get_sheets()
    data = profile_sheet.get_all_records()
    row_data = [str(profile.get(col, "")) for col in PROFILE_COLUMNS]
    if not data:
        profile_sheet.append_row(row_data)
    else:
        profile_sheet.update("A2", [row_data])
    st.cache_data.clear()
        

def get_latest_weight(df):
    """Get the most recently logged weight."""
    weight_df = df[df["weight_lbs"].notna() & (df["weight_lbs"] != "")]
    if weight_df.empty:
        return None
    return float(weight_df.iloc[-1]["weight_lbs"])

def get_streak(df):
    """Calculate how many consecutive days have been logged up to today."""
    if df.empty:
        return 0
    today = pd.Timestamp(date.today())
    logged_dates = set(df["date"].dt.normalize())
    streak = 0
    check_date = today
    while check_date in logged_dates:
        streak += 1
        check_date -= pd.Timedelta(days=1)
    return streak
