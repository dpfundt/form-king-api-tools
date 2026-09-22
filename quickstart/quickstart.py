"""
Form King Modellers API - Quickstart
Pulls the next 7 days of meetings and saves them as a CSV you can open in Excel.
Works with the free test key. Requires: pip install requests
"""
import os
import sys
import requests

API_KEY = os.environ.get("FK_API_KEY", "FK-TEST-API-KEY")   # swap in your own key
BASE_URL = "https://api.formking.com.au"

# Optional filters - edit to taste (see the API docs for valid values)
STATES = ""            # e.g. "VIC" or "" for all states
GRADES = "M,P,C"                # M = Metro, P = Provincial, C = Country
STATUSES = "FINAL_OR_RESULTED"  # drop nominations / weights / abandoned meetings
FLATTEN = "race"              # meeting | race | entry  (one row per ...)

params = {"format": "csv", "flatten": FLATTEN}
if STATES:   params["states"] = STATES
if GRADES:   params["grades"] = GRADES
if STATUSES: params["statuses"] = STATUSES

resp = requests.get(
    f"{BASE_URL}/b2c/meetings/upcoming",
    headers={"x-api-key": API_KEY},
    params=params,
    timeout=60,
    allow_redirects=True,      # large responses redirect (307) to a download link
)

if resp.status_code == 401:
    sys.exit("401: API key missing or invalid. Check FK_API_KEY.")
if resp.status_code == 402:
    sys.exit("402: Out of credits. Top up via My Subscriptions on Form King Web.")
if resp.status_code == 429:
    sys.exit("429: Rate limited. Wait a minute and try again.")
resp.raise_for_status()

out = "upcoming_meetings.csv"
with open(out, "wb") as f:
    f.write(resp.content)

rows = resp.text.count("\n") - 1
print(f"Saved {rows} rows to {out}. Open it in Excel or Google Sheets.")
print("Cost: 1 credit.")