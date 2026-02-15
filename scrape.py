import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

URL = "PASTE_THE_PUBLIC_SCHEDULE_URL_HERE"

def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def parse_schedule(html):
    soup = BeautifulSoup(html, "html.parser")

    classes = []

    # Adjust selector to actual schedule table
    rows = soup.select("table tr")

    for row in rows[1:]:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) >= 4:
            classes.append({
                "name": cols[0],
                "date": cols[1],
                "time": cols[2],
                "location": cols[3],
            })

    return classes

def save_json(data):
    with open("schedule.json", "w") as f:
        json.dump({
            "last_updated": datetime.utcnow().isoformat(),
            "classes": data
        }, f, indent=2)

if __name__ == "__main__":
    html = fetch_page()
    data = parse_schedule(html)
    save_json(data)
    print(f"Saved {len(data)} classes.")
