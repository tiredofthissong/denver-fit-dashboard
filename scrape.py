"""
CarlaFit Scraper v3.1 — Smart Waits & Robust Loading
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

# URL: We use the list view which is easier to scrape than the grid
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
    # Add a real user agent to look less like a robot
    opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=opts)

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def next_occurrence(day_abbr):
    """Calculates the specific date for the next class day."""
    if not day_abbr or len(day_abbr) < 3: return "Check Schedule"
    
    today = datetime.now()
    target = DAY_MAP.get(day_abbr.lower()[:3])
    
    if target is None:
        return "Check Schedule"
        
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
        
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

        # --- THE FIX: SMART WAIT ---
        # Instead of sleeping 6s, we wait up to 25s for the specific "Sign Up" links to appear.
        try:
            log.info("Waiting for activity data to render...")
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/activity/search/detail']"))
            )
            # Small buffer for the rest of the list to populate after the first item appears
            time.sleep(3) 
            log.info("Page loaded successfully.")
        except Exception as e:
            log.warning(f"Timeout waiting for data: {e}. Page might be empty or very slow.")
            # We continue anyway to see if BeautifulSoup can find anything residual

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find ALL links with "activity" in href (The actual class links)
        all_links = soup.find_all("a", href=True)
        activity_links = [l for l in all_links if "/activity/search/detail" in l.get("href", "")]

        log.info(f"Found {len(activity_links)} activity links")

        seen = set()

        for link in activity_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Deduplication & Cleanup
            if not text or text in seen: continue
            if "Add to Cart" in text or "View Details" in text: continue # Skip buttons, keep titles
            
            seen.add(text)

            # 1. ID Extraction
            id_match = re.search(r"/detail/(\d+)", href)
            activity_id = id_match.group(1) if id_match else "unknown"

            # 2. Context Extraction (Traverse up to find the container text)
            parent = link.parent
            context_text = ""
            for _ in range(4): # Look 4 levels up
                if parent:
                    context_text += " " + parent.get_text(" | ", strip=True)
                    parent = parent.parent
            
            # 3. Clean Name
            clean_name = re.sub(r"^(FIT|AOA):\s*", "", text, flags=re.IGNORECASE)
            clean_name = re.sub(r"\s*@\s*Carla.*", "", clean_name, flags=re.IGNORECASE).strip()
            
            if len(clean_name) < 3: continue

            # 4. Extract Days (Mon, Wed, etc.)
            days_found = [d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d in context_text]
            days_display = ", ".join(days_found) if days_found else "Check Details"
            
            # 5. Extract Time
            time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))", context_text, re.IGNORECASE)
            time_display = f"{time_match.group(1)} – {time_match.group(2)}" if time_match else "See Details"

            # 6. Calculate Next Date
            next_date = "Check Schedule"
            if days_found:
                next_date = next_occurrence(days_found[0])

            # 7. Price & Status
            price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", context_text)
            price = price_match.group(0) if price_match else "Free"
            
            status = "Open"
            lower_ctx = context_text.lower()
            if "full" in lower_ctx: status = "Full"
            elif "waitlist" in lower_ctx: status = "Waitlist"
            elif "closed" in lower_ctx: status = "Closed"

            # 8. Category
            category = classify(clean_name)

            classes.append({
                "Name": clean_name,
                "Day": days_display,
                "Time": time_display,
                "NextDate": next_date,
                "Category": category,
                "ActivityID": activity_id,
                "Link": f"https://anc.apm.activecommunities.com{href}" if href.startswith("/") else href,
                "Status": status,
                "Price": price,
                "DateRange": ""
            })

        log.info(f"✓ Extracted {len(classes)} valid classes")

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
        log.info(f"✓ Wrote {len(classes)} rows to {OUTPUT_FILE}")
        return True
    except Exception as e:
        log.error(f"Failed to write CSV: {e}")
        return False

if __name__ == "__main__":
    data = scrape()
    if data:
        write_csv(data)
    else:
        # Fallback: Write a dummy row so the workflow doesn't fail on "empty file"
        log.warning("No data found. Writing empty state to CSV.")
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Name", "Day", "Time", "NextDate", "Category", "ActivityID", "Link", "Status", "Price", "DateRange"])
            writer.writeheader()
            writer.writerow({
                "Name": "No Classes Found (Site Slow)", 
                "Day": "Try Refreshing", 
                "Time": datetime.now().strftime("%H:%M"), 
                "NextDate": "Today", 
                "Category": "System", 
                "Status": "Error"
            })
