"""
CarlaFit Scraper v2.0 — Production Grade
=========================================
Scrapes the Denver ActiveNet "Activity Search" page for Carla Madison Rec Center.
Outputs a clean CSV with: Name, Day, Time, NextDate, Category, ActivityID, Link, Status, Price, DateRange

Key improvements over v1:
- Uses Selenium with explicit waits (not just sleep)
- Parses structured card data instead of regex on raw text
- Calculates next occurrence dates for recurring classes
- Filters to Carla Madison only
- Proper error handling and logging
- Outputs sorted by next occurrence
"""

import time
import csv
import re
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- CONFIG ---
TARGET_URL = (
    "https://anc.apm.activecommunities.com/denver/activity/search"
    "?onlineSiteId=0&activity_select_param=2"
    "&activity_keyword=Carla%20Madison&viewMode=list"
)
OUTPUT_FILE = "fitness_schedule.csv"
LOCATION_FILTER = "carla madison"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("carlafit")


def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)


# --- DATE HELPERS ---
DAY_ABBREVS = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

def parse_days(text: str) -> list[str]:
    """Extract day names from strings like 'Mon,Wed,Fri' or 'Tue 10:45 AM'."""
    text_lower = text.lower()
    found = []
    for abbr in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        if abbr in text_lower:
            found.append(abbr.capitalize())
    return found if found else []


def next_occurrence(day_abbr: str) -> datetime:
    """Return the next occurrence of a weekday (e.g. 'Mon') from today."""
    today = datetime.now()
    target = DAY_ABBREVS.get(day_abbr.lower()[:3], None)
    if target is None:
        return today
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        # If it's today, still show today
        pass
    return today + timedelta(days=days_ahead)


def format_date(dt: datetime) -> str:
    return dt.strftime("%a, %b %d")


# --- CATEGORY CLASSIFIER ---
CATEGORY_MAP = {
    "yoga": "Yoga",
    "pilates": "Mind & Body",
    "stretch": "Mind & Body",
    "tai chi": "Mind & Body",
    "meditation": "Mind & Body",
    "cycle": "Cardio",
    "cycling": "Cardio",
    "spin": "Cardio",
    "zumba": "Cardio",
    "dance": "Cardio",
    "hiit": "Cardio",
    "cardio": "Cardio",
    "step": "Cardio",
    "kickbox": "Cardio",
    "aqua": "Aqua",
    "swim": "Aqua",
    "water": "Aqua",
    "pool": "Aqua",
    "pump": "Strength",
    "strength": "Strength",
    "tone": "Strength",
    "weight": "Strength",
    "boot camp": "Strength",
    "bootcamp": "Strength",
    "circuit": "Strength",
    "barre": "Strength",
    "pickleball": "Sports",
    "basketball": "Sports",
    "volleyball": "Sports",
    "tennis": "Sports",
    "badminton": "Sports",
    "gym": "Open Gym",
    "open gym": "Open Gym",
    "drop-in": "Open Gym",
}

def classify(name: str) -> str:
    low = name.lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in low:
            return cat
    # Default based on common Denver prefix patterns
    if low.startswith("fit:"):
        return "Fitness"
    if low.startswith("aoa:"):
        return "Active Older Adults"
    return "Fitness"


# --- SCRAPER ---
def scroll_to_load_all(driver, pause=2, max_scrolls=30):
    """Scroll down to trigger lazy-loading of all results."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            log.info(f"Finished scrolling after {i+1} scrolls")
            break
        last_height = new_height


def scrape():
    driver = setup_driver()
    classes = []

    try:
        log.info(f"Loading: {TARGET_URL}")
        driver.get(TARGET_URL)

        # Wait for page to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            log.info("Page loaded successfully")
        except:
            log.warning("Page load timeout, continuing anyway")

        time.sleep(4)  # Extra buffer for JS rendering

        # Scroll to load all results
        log.info("Scrolling to load lazy-loaded results...")
        scroll_to_load_all(driver, pause=1.5, max_scrolls=20)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all activity links — these are the primary anchors
        activity_links = soup.find_all("a", href=re.compile(r"/activity/search/detail/\d+"))
        log.info(f"Found {len(activity_links)} activity links")

        if len(activity_links) == 0:
            log.warning("No activity links found. Trying alternate selectors...")
            # Try broader search
            all_links = soup.find_all("a", href=True)
            activity_links = [l for l in all_links if "activity" in l.get("href", "").lower()]
            log.info(f"Alternate search found {len(activity_links)} links")

        seen_ids = set()

        for link in activity_links:
            href = link.get("href", "")
            activity_id_match = re.search(r"/detail/(\d+)", href)
            if not activity_id_match:
                continue
            activity_id = activity_id_match.group(1)

            if activity_id in seen_ids:
                continue
            seen_ids.add(activity_id)

            # Get the parent card/row container
            card = link
            for _ in range(8):
                if card.parent:
                    card = card.parent
                    # Look for a container that has enough text content
                    card_text = card.get_text(" ", strip=True)
                    if len(card_text) > 50 and activity_id in card_text.replace("#", ""):
                        break

            card_text = card.get_text(" | ", strip=True)

            # --- FILTER: Only Carla Madison ---
            if LOCATION_FILTER not in card_text.lower():
                continue

            # --- EXTRACT CLASS NAME ---
            raw_name = link.get_text(strip=True)
            # Clean: remove "@ Carla Madison" suffix, "FIT:"/"AOA:" prefixes
            clean_name = re.sub(r"\s*@\s*Carla\s*Madison.*", "", raw_name, flags=re.IGNORECASE)
            clean_name = re.sub(r"^(FIT|AOA):\s*", "", clean_name, flags=re.IGNORECASE).strip()

            # --- EXTRACT TIME ---
            time_match = re.search(
                r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))",
                card_text, re.IGNORECASE
            )
            start_time = time_match.group(1).strip() if time_match else ""
            end_time = time_match.group(2).strip() if time_match else ""
            time_display = f"{start_time} – {end_time}" if start_time else "See Details"

            # --- EXTRACT DAYS ---
            days = parse_days(card_text)
            days_display = ", ".join(days) if days else "See Details"

            # --- CALCULATE NEXT DATE ---
            if days:
                next_dates = [next_occurrence(d) for d in days]
                nearest = min(next_dates)
                next_date_display = format_date(nearest)
                sort_key = nearest.strftime("%Y-%m-%d")
            else:
                next_date_display = "Check Schedule"
                sort_key = "9999-99-99"

            # --- EXTRACT PRICE ---
            price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", card_text)
            price = price_match.group(0) if price_match else "Free"

            # --- EXTRACT STATUS ---
            status = "Open"
            if "full" in card_text.lower():
                status = "Full"
            elif "in progress" in card_text.lower():
                status = "In Progress"
            elif "waitlist" in card_text.lower():
                status = "Waitlist"

            # --- EXTRACT DATE RANGE ---
            date_range_match = re.search(
                r"(\w+ \d{1,2},?\s*\d{4})\s*(?:to|-)\s*(\w+ \d{1,2},?\s*\d{4})",
                card_text
            )
            date_range = (
                f"{date_range_match.group(1)} – {date_range_match.group(2)}"
                if date_range_match else ""
            )

            # --- BUILD SIGNUP LINK ---
            signup_url = f"https://anc.apm.activecommunities.com{href}" if href.startswith("/") else href

            # --- CATEGORY ---
            category = classify(clean_name)

            classes.append({
                "Name": clean_name,
                "Day": days_display,
                "Time": time_display,
                "NextDate": next_date_display,
                "SortKey": sort_key,
                "Category": category,
                "ActivityID": activity_id,
                "Link": signup_url,
                "Status": status,
                "Price": price,
                "DateRange": date_range,
            })

        # Sort by next occurrence
        classes.sort(key=lambda x: x["SortKey"])

        log.info(f"Extracted {len(classes)} Carla Madison classes")

    except Exception as e:
        log.error(f"Scrape failed: {e}", exc_info=True)
        log.warning("Scraping failed — CSV will not update this run")

    finally:
        try:
            driver.quit()
        except:
            pass

    if len(classes) == 0:
        log.warning("No classes extracted. Check website structure.")
    else:
        log.info(f"Success: {len(classes)} classes extracted")

    return classes


def write_csv(classes: list[dict]):
    fieldnames = [
        "Name", "Day", "Time", "NextDate", "Category",
        "ActivityID", "Link", "Status", "Price", "DateRange"
    ]
    try:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(classes)
        log.info(f"✓ Wrote {len(classes)} rows to {OUTPUT_FILE}")
        return True
    except Exception as e:
        log.error(f"Failed to write CSV: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("CarlaFit Scraper v2.0 — Starting")
    print("=" * 60)

    data = scrape()

    if data and len(data) > 0:
        success = write_csv(data)
        if success:
            print("\n" + "=" * 60)
            print(f"✓ SUCCESS: {len(data)} classes scraped and saved")
            print("=" * 60)
        else:
            print("\n✗ ERROR: Failed to write CSV")
    else:
        print("\n✗ WARNING: No classes found — CSV will not be updated")
        print("Check the website structure or network connectivity")
        print("Previous CSV remains unchanged")
