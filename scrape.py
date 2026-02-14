"""
CarlaFit Scraper v3.2 — Long Wait & Broad Selectors
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

# URL: List view
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
    opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # --- STEALTH FLAGS (The Fix) ---
    # These hide the "Automation" status from the website
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(options=opts)

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def next_occurrence(day_abbr):
    if not day_abbr or len(day_abbr) < 3: return "Check Schedule"
    today = datetime.now()
    target = DAY_MAP.get(day_abbr.lower()[:3])
    if target is None: return "Check Schedule"
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0: days_ahead = 7
    next_date = today + timedelta(days=days_ahead)
    return next_date.strftime("%a, %b %d")

def classify(name):
    low = name.lower()
    if any(x in low for x in ["yoga", "pilates", "stretch", "tai chi"]): return "Yoga"
    if any(x in low for x in ["cycle", "cycling", "spin", "zumba", "dance", "hiit", "cardio", "kickbox"]): return "Cardio"
    if any(x in low for x in ["aqua", "swim", "water", "pool"]): return "Aqua"
    if any(x in low for x in ["pump", "strength", "tone", "weight", "boot", "circuit", "barre"]): return "Strength"
    if any(x in low for x in ["pickleball", "basketball", "volleyball", "tennis"]): return "Sports"
    if "aoa" in low or "older adult" in low: return "Active Older Adults"
    if "gym" in low or "drop" in low: return "Open Gym"
    return "Fitness"

def scrape():
    driver = setup_driver()
    classes = []

    try:
        log.info(f"Loading: {TARGET_URL}")
        driver.get(TARGET_URL)

        # --- THE FIX: WAIT 60 SECONDS FOR ANY DATA ---
        try:
            log.info("Waiting up to 60s for page load...")
            # We look for 'tr' (table rows) which is broader than looking for specific links
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "tr"))
            )
            # Force a hard sleep to allow JavaScript to finish rendering the list
            time.sleep(10)
            log.info("Page loaded.")
        except Exception as e:
            log.warning(f"Timeout: {e}. Attempting to parse anyway...")

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all table rows
        rows = soup.find_all("tr")
        log.info(f"Found {len(rows)} rows to process")

        seen = set()

        for row in rows:
            text = row.get_text(" | ", strip=True)
            
            # Simple Filter: Must contain our gym name
            if "Carla Madison" not in text: continue
            
            # Dedupe
            if text in seen: continue
            seen.add(text)

            # Extract Name
            clean_name = re.sub(r"^(FIT|AOA):\s*", "", text, flags=re.IGNORECASE)
            # Grab just the name part before the location
            match = re.search(r"^(.*?)\s*\|\s*#", clean_name)
            if match:
                clean_name = match.group(1).strip()
            clean_name = re.sub(r"\s*@\s*Carla.*", "", clean_name).strip()

            if len(clean_name) < 3: continue

            # Extract Days
            days_found = [d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d in text]
            days_display = ", ".join(days_found) if days_found else "Check Details"

            # Extract Time
            time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))", text, re.IGNORECASE)
            time_display = f"{time_match.group(1)} – {time_match.group(2)}" if time_match else "See Details"

            # Next Date
            next_date = next_occurrence(days_found[0]) if days_found else "Check Schedule"

            # Price & Status
            price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
            price = price_match.group(0) if price_match else "Free"
            
            status = "Open"
            if "Full" in text: status = "Full"
            elif "Waitlist" in text: status = "Waitlist"

            # Link - Try to find 'a' tag in row
            link_tag = row.find("a", href=True)
            href = link_tag['href'] if link_tag else ""
            if href and not href.startswith("http"):
                href = f"https://anc.apm.activecommunities.com{href}"
            
            # ID
            id_match = re.search(r"/detail/(\d+)", href)
            activity_id = id_match.group(1) if id_match else "000"

            classes.append({
                "Name": clean_name,
                "Day": days_display,
                "Time": time_display,
                "NextDate": next_date,
                "Category": classify(clean_name),
                "ActivityID": activity_id,
                "Link": href or TARGET_URL,
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
        except: pass

    return classes

def write_csv(classes):
    fieldnames = ["Name", "Day", "Time", "NextDate", "Category", "ActivityID", "Link", "Status", "Price", "DateRange"]
    try:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(classes)
        return True
    except Exception as e:
        log.error(f"Failed to write CSV: {e}")
        return False

if __name__ == "__main__":
    data = scrape()
    if data:
        write_csv(data)
    else:
        # Emergency Placeholder so dashboard shows SOMETHING
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Name", "Day", "Time", "NextDate", "Category", "ActivityID", "Link", "Status", "Price", "DateRange"])
            writer.writeheader()
            writer.writerow({
                "Name": "Site Loading Slow...", 
                "Day": "Try refreshing", 
                "Time": datetime.now().strftime("%H:%M"), 
                "NextDate": "Today", 
                "Category": "System", 
                "Status": "Error"
            })
