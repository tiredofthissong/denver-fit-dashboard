#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ACCOUNT_ID = 522
LOCATION_FILTER = "Carla Madison"
API_URL = f"https://www.groupexpro.com/schedule/embed/json.php?schedule&a={ACCOUNT_ID}"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "schedule.json"

CATEGORY_PATTERNS = {
    "yoga": r"\b(yoga|vinyasa)\b",
    "pilates": r"\bpilates\b",
    "spin": r"\b(spin|cycling|cycle)\b",
    "strength": r"\b(strength|weight|lift|barbell|functional fit)\b",
    "cardio": r"\b(cardio|hiit|bootcamp|aerobic)\b",
    "aqua": r"\b(swim|aqua|pool|water aerobics)\b",
    "dance": r"\b(dance|zumba|barre)\b",
    "mind_body": r"\b(tai chi|meditation|stretch|slow flow)\b",
}

def fetch_schedule():
    print(f"Fetching from: {API_URL}")
    req = Request(API_URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    try:
        data = json.loads(raw)
        return data.get("aaData", [])
    except json.JSONDecodeError:
        match = re.search(r'"aaData"\s*:\s*(\[.*\])', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        sys.exit(1)

def detect_category(name):
    name_lower = name.lower()
    for cat, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, name_lower):
            return cat
    return "general"

def parse_class(row):
    if len(row) < 9:
        return None
    try:
        date_obj = datetime.strptime(row[0], "%A, %B %d, %Y")
        iso_date = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        iso_date = row[0]
    instructor = row[6]
    if instructor in ("NA -   No Instructor .", "Staff", "NA"):
        instructor = None
    return {
        "name": row[2],
        "date": iso_date,
        "time": row[1],
        "location": row[8],
        "room": row[4].replace("&nbsp;", "").strip() or None,
        "instructor": instructor,
        "duration_minutes": int(row[7]) if row[7].isdigit() else None,
        "category": detect_category(row[2]),
    }

def main():
    print("=" * 50)
    print("Denver Fit Dashboard — Schedule Scraper")
    print("=" * 50)
    raw_data = fetch_schedule()
    print(f"Fetched {len(raw_data)} total classes")
    all_classes = [parse_class(row) for row in raw_data if parse_class(row)]
    filtered = [c for c in all_classes if c.get("location") == LOCATION_FILTER]
    print(f"Filtered to {len(filtered)} classes at {LOCATION_FILTER}")
    filtered.sort(key=lambda c: (c["date"], c["time"]))
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "location": LOCATION_FILTER, "class_count": len(filtered), "classes": filtered}, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")
    for cls in filtered[:5]:
        print(f"  {cls['date']} {cls['time']} - {cls['name']}")
    print("Done!")

if __name__ == "__main__":
    main()
