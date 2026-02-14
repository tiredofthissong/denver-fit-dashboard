"""
CarlaFit Scraper v5.0 — Undetected Mode (Required)
"""
import time
import csv
import re
import logging
from datetime import datetime, timedelta
import undetected_chromedriver as uc
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
    """
    Initializes Undetected Chromedriver. 
    This is REQUIRED to bypass the 'Timeout/White Screen' blocks.
    """
    opts = uc.ChromeOptions()
    opts.add_argument("--headless=new") 
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    
    # Initialize UC driver (version_main=None auto-matches Chrome)
    driver = uc.Chrome(options=opts, version_main=None)
    return driver

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def next_occurrence(day_abbr):
    if not day_abbr or len(day_abbr) < 3: return "Check Sched"
    today = datetime.now()
    target = DAY_MAP.get(day_abbr.lower()[:3])
    if target is None: return "Check Sched"
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0: days_ahead = 7
    next_date = today + timedelta(days=days_ahead)
    return next_date.strftime("%a, %b %d")

def classify(name):
    low = name.lower()
    if any(x in low for x in ["yoga", "pilates", "stretch"]): return "Yoga"
    if any(x in low for x in ["cycle", "cycling", "spin", "zumba", "dance", "hiit", "cardio", "kickbox"]): return "Cardio"
    if any(x in low for x in ["aqua", "swim", "water", "pool"]): return "Aqua"
    if any(x in low for x in ["pump", "strength", "tone", "weight", "boot", "circuit", "barre"]): return "Strength"
    if any(x in low for x in ["pickleball", "basketball", "volleyball", "tennis"]): return "Sports"
    if "aoa" in low or "older adult" in low: return "Active Older Adults"
    return "Fitness"

def scrape():
    driver = None
    classes = []
    try:
        log.info("🚀 Starting Undetected Driver...")
        driver = setup_driver()
        
        log.info(f"Loading: {TARGET_URL}")
        driver.get(TARGET_URL)

        # Smart Wait: Look for the 'tbody' tag (Container for list results)
        try:
            log.info("Waiting for data table...")
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
            time.sleep(5) # Let the DOM settle
            log.info("Page loaded.")
        except Exception as e:
            log.warning(f"Wait timeout: {e}. Attempting to parse anyway...")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        rows = soup.find_all("tr")
        log.info(f"Found {len(rows)} potential rows")

        seen = set()
        for row in rows:
            text = row.get_text(" | ", strip=True)
            if "Carla Madison" not in text: continue
            if text in seen: continue
            seen.add(text)

            # Name Parsing
            clean_name = re.sub(r"^(FIT|AOA):\s*", "", text, flags=re.IGNORECASE)
            match = re.search(r"^(.*?)\s*\|\s*#", clean_name)
            if match: clean_name = match.group(1).strip()
            clean_name = re.sub(r"\s*@\s*Carla.*", "", clean_name).strip()
            if len(clean_name) < 3: continue

            # Day/Time Parsing
            days_found = [d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d in text]
            day_disp = ", ".join(days_found) if days_found else "Check Details"
            
            time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))", text, re.IGNORECASE)
            time_disp = f"{time_match.group(1)} – {time_match.group(2)}" if time_match else "See Details"

            # Metadata
            status = "Open"
            if "Full" in text: status = "Full"
            elif "Waitlist" in text: status = "Waitlist"
            
            link_tag = row.find("a", href=True)
            href = link_tag['href'] if link_tag else ""
            if href and not href.startswith("http"): href = f"https://anc.apm.activecommunities.com{href}"
            
            id_match = re.search(r"/detail/(\d+)", href)
            act_id = id_match.group(1) if id_match else "000"

            classes.append({
                "Name": clean_name,
                "Day": day_disp,
                "Time": time_disp,
                "NextDate": next_occurrence(days_found[0]) if days_found else "Check Sched",
                "Category": classify(clean_name),
                "ActivityID": act_id,
                "Link": href or TARGET_URL,
                "Status": status,
                "Price": "Mem/DropIn",
                "DateRange": ""
            })

    except Exception as e:
        log.error(f"Scrape Error: {e}")
    finally:
        if driver:
            driver.quit()

    return classes

if __name__ == "__main__":
    data = scrape()
    
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Name", "Day", "Time", "NextDate", "Category", "ActivityID", "Link", "Status", "Price", "DateRange"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        if data:
            writer.writerows(data)
            log.info(f"✓ Success: {len(data)} classes saved.")
        else:
            writer.writerow({
                "Name": "System Syncing...", 
                "Day": "Try again later", 
                "Time": datetime.now().strftime("%H:%M"), 
                "Category": "System", 
                "Status": "Error"
            })
            log.warning("No data found.")
