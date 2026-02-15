#!/usr/bin/env python3
"""
Denver Fit Dashboard — GroupEx Pro API Scraper
"""

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
    req = Request(API_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; DenverFitDashboard/1.0)",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)
    
    try:
        data = json.loads(raw)
        return data.get("aaData", [])
    except json.JSONDecodeError:
        match = re.search(r'"aaData"\s*:\s*(\[.*\])', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        print("Error: Could not parse API response")
        sys.exit(1)

def detect_category(name):
    name_lower = name.lower()
    for category, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, name_lower, re.IGNORECASE):
            return category
    return "general"

def parse_class(row):
    if len(row) < 9:
        return None
    
    date_str = row[0]
    time_str = row[1]
    name = row[2]
    room = row[4].replace("&nbsp;", "").strip()
    category_raw = row[5]
    instructor = row[6]
    duration = row[7]
    location = row[8]
    
    try:
        date_obj = datetime.strptime(date_str, "%A, %B %d, %Y")
        iso_date = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        iso_date = date_str
    
    if instructor in ("NA -   No Instructor .", "Staff", "NA"):
        instructor = None
    
    return {
        "name": name,
        "date": iso_date,
        "time": time_str,
        "location": location,
        "room": room if room else None,
        "instructor": instructor,
        "duration_minutes": int(duration) if duration.isdigit() else None,
        "category": detect_category(name),
    }

def save_schedule(classes):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    classes.sort(key=lambda c: (c["date"], c["time"]))
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "location": LOCATION_FILTER,
        "class_count": len(classes),
        "classes": classes,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(classes)} classes to {OUTPUT_FILE}")

def main():
    print("=" * 50)
    print("Denver Fit Dashboard — Schedule Scraper")
    print("=" * 50)
    
    raw_data = fetch_schedule()
    print(f"Fetched {len(raw_data)} total classes")
    
    all_classes = [parse_class(row) for row in raw_data]
    all_classes = [c for c in all_classes if c]
    
    filtered = [c for c in all_classes if c.get("location") == LOCATION_FILTER]
    print(f"Filtered to {len(filtered)} classes at {LOCATION_FILTER}")
    
    save_schedule(filtered)
    
    print("\nUpcoming classes:")
    for cls in filtered[:5]:
        print(f"  {cls['date']} {cls['time']} - {cls['name']}")
    
    print("\n✓ Done!")

if __name__ == "__main__":
    main()
