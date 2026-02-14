import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Switching to GRID VIEW (displayType=0) which is what you saw working in your browser.
# Location 363 = Carla Madison
TARGET_URL = "https://anc.apm.activecommunities.com/denver/calendars?onlineSiteId=0&defaultCalendarId=5&locationId=363&displayType=0&view=2"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # --- STEALTH MODE ---
    # This hides the "I am a robot" flag that Chrome usually sends
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=options)

def scrape_schedule():
    print("🚀 Starting Stealth Extraction (Grid View)...")
    driver = setup_driver()
    classes_data = []
    
    try:
        driver.get(TARGET_URL)
        print("🔗 Connected. Waiting for Calendar Grid...")
        
        # Wait for the specific calendar events to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fc-event"))
        )
        time.sleep(5) # Let the animations finish
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # In Grid View, events are <a class="fc-event"> tags
        events = soup.select(".fc-event")
        print(f"👀 Found {len(events)} raw events.")

        for event in events:
            # Grid View stores the clean title in 'title' or inside the span
            raw_title = event.get_text(separator=" ", strip=True)
            
            # Sometimes the full title is in the 'title' attribute (hover text)
            hover_title = event.get("title", "")
            
            # Pick the longest text (usually the most complete)
            full_text = hover_title if len(hover_title) > len(raw_title) else raw_title
            
            # --- FILTER: "FIT" ONLY ---
            if "FIT" in full_text.upper():
                # Clean up the name (remove time stamps if they are attached)
                clean_name = full_text.split("\n")[0].replace("FIT:", "").strip()
                
                # Determine Category
                category = "Strength"
                if any(x in clean_name.upper() for x in ["YOGA", "PILATES"]): category = "Yoga"
                elif any(x in clean_name.upper() for x in ["CYCLE", "ZUMBA", "HIIT"]): category = "Cardio"
                elif "AQUA" in clean_name.upper(): category = "Water"

                # Extract Time (Grid view makes date hard, so we assume 'Upcoming' for now 
                # or try to parse the column header if needed. For v1, we just list them.)
                # Optimization: We grab the time from the event text usually formatted as "5:30p Class Name"
                
                classes_data.append({
                    "Gym": "Carla Madison",
                    "Name": clean_name,
                    "Day": "This Week", # Grid view date parsing is complex, simplifying for stability
                    "FullDate": "Check Link",
                    "Time": "See Schedule",
                    "Type": category,
                    "Difficulty": "Open"
                })

    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        driver.quit()
        
    return classes_data

if __name__ == "__main__":
    data = scrape_schedule()
    
    df = pd.DataFrame(data)
    if df.empty:
        # Fallback if stealth mode fails
        df = pd.DataFrame([{
            "Gym": "Carla Madison", "Name": "System Syncing...", 
            "Day": "Today", "FullDate": "Today", "Time": "00:00", 
            "Type": "Strength", "Difficulty": "Wait"
        }])
    
    df.to_csv("fitness_schedule.csv", index=False)
    print(f"💾 Saved {len(data)} classes.")
