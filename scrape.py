"""
CarlaFit Scraper v3.0 — Simplified & More Lenient
"""
import time
import csv
import re
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

TARGET_URL = "https://anc.apm.activecommunities.com/denver/activity/search?onlineSiteId=0&activity_select_param=2&activity_keyword=Carla%20Madison&viewMode=list"
OUTPUT_FILE = "fitness_schedule.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("carlafit")

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def next_occurrence(day_abbr):
    today = datetime.now()
    target = DAY_MAP.get(day_abbr.lower()[:3])
    if target is None:
        return "Check Schedule"
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_date = today + timedelta(days=days_ahead)
    return next_date.strftime("%a, %b %d")

def parse_days(text):
    found = []
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        if day.lower() in text.lower():
            found.append(day)
    return ", ".join(found) if found else "See Details"

def classify(name):
    low = name.lower()
    if any(x in low for x in ["yoga", "pilates", "stretch", "tai chi"]):
        return "Yoga"
    if any(x in low for x in ["cycle", "cycling", "spin", "zumba", "dance", "hiit", "cardio", "kickbox"]):
        return "Cardio"
    if any(x in low for x in ["aqua", "swim", "water", "pool"]):
        return "Aqua"
    if any(x in low for x in ["pump", "strength", "tone", "weight", "boot", "circuit", "barre"]):
        return "Strength"
    if any(x in low for x in ["pickleball", "basketball", "volleyball", "tennis"]):
        return "Sports"
    if "aoa" in low or "older adult" in low:
        return "Active Older Adults"
    if "gym" in low or "drop" in low:
        return "Open Gym"
    return "Fitness"

def scrape():
    driver = setup_driver()
    classes = []

    try:
        log.info(f"Loading: {TARGET_URL}")
        driver.get(TARGET_URL)
        time.sleep(6)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find ALL links with "activity" in href
        all_links = soup.find_all("a", href=True)
        activity_links = [l for l in all_links if "/activity/" in l.get("href", "")]

        log.info(f"Found {len(activity_links)} activity links")

        seen = set()

        for link in activity_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Skip if empty or duplicate
            if not text or text in seen:
                continue
            seen.add(text)

            # Extract ID from URL if possible
            id_match = re.search(r"/detail/(\d+)", href)
            activity_id = id_match.group(1) if id_match else "unknown"

            # Get surrounding context (parent elements)
            parent = link.parent
            context_text = ""
            for _ in range(5):
                if parent:
                    context_text = parent.get_text(" | ", strip=True)
                    if len(context_text) > 100:
                        break
                    parent = parent.parent

            # Skip if no context found
            if len(context_text) < 20:
                continue

            # Clean name
            clean_name = re.sub(r"^(FIT|AOA):\s*", "", text, flags=re.IGNORECASE)
            clean_name = re.sub(r"\s*@\s*Carla.*", "", clean_name, flags=re.IGNORECASE).strip()

            if not clean_name or len(clean_name) < 3:
                continue

            # Extract time
            time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))", context_text, re.IGNORECASE)
            if time_match:
                time_display = f"{time_match.group(1)} – {time_match.group(2)}"
            else:
                time_display = "See Details"

            # Extract days
            days_display = parse_days(context_text)

            # Calculate next date
            if days_display and days_display != "See Details":
                first_day = days_display.split(",")[0].strip()
                next_date = next_occurrence(first_day)
            else:
                next_date = "Check Schedule"

            # Extract price
            price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", context_text)
            price = price_match.group(0) if price_match else "Free"

            # Status
            status = "Open"
            if "full" in context_text.lower():
                status = "Full"
            elif "progress" in context_text.lower():
                status = "In Progress"
            elif "waitlist" in context_text.lower():
                status = "Waitlist"

            # Build link
            if href.startswith("/"):
                signup_url = f"https://anc.apm.activecommunities.com{href}"
            else:
                signup_url = href

            # Category
            category = classify(clean_name)

            # Add to list
            classes.append({
                "Name": clean_name,
                "Day": days_display,
                "Time": time_display,
                "NextDate": next_date,
                "Category": category,
                "ActivityID": activity_id,
                "Link": signup_url,
                "Status": status,
                "Price": price,
                "DateRange": ""
            })

        log.info(f"✓ Extracted {len(classes)} classes")

    except Exception as e:
        log.error(f"Scrape failed: {e}", exc_info=True)
    finally:
        try:
            driver.quit()
        except:
            pass

    return classes

def write_csv(classes):
    fieldnames = ["Name", "Day", "Time", "NextDate", "Category", "ActivityID", "Link", "Status", "Price", "DateRange"]
    try:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(classes)
        log.info(f"✓ Wrote {len(classes)} rows to {OUTPUT_FILE}")
        return True
    except Exception as e:
        log.error(f"Failed to write CSV: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CarlaFit Scraper v3.0 — Simplified")
    print("=" * 60)

    data = scrape()

    if data and len(data) > 0:
        success = write_csv(data)
        if success:
            print(f"\n✓ SUCCESS: {len(data)} classes scraped")
            print("=" * 60)
        else:
            print("\n✗ ERROR: Failed to write CSV")
    else:
        print("\n✗ WARNING: No classes found")
        print("Previous CSV remains unchanged")
