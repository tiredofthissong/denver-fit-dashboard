import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION ---
# We use the SEARCH URL. It is lighter and easier to scrape than the Calendar.
# We hard-filter for "FIT" keyword in the URL itself.
TARGET_URL = "https://anc.apm.activecommunities.com/denver/activity/search?onlineSiteId=0&activity_select_param=2&activity_keyword=FIT&viewMode=list"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080") # Force Desktop View
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_schedule():
    driver = setup_driver()
    classes_data = []
    
    try:
        driver.get(TARGET_URL)
        print("🔗 Search Page Loaded.")
        
        # 1. Force a Scroll to trigger any lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5) # Wait for text to settle

        # 2. Grab the Raw HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 3. "Nuclear" Text Search
        # Instead of looking for a table, we grab ALL text and look for "Carla Madison" blocks.
        # ActiveNet Search results usually group text in 'cards' or rows.
        
        # Find all container elements that might hold a class
        # In Search view, these are often divs with class 'activity-card' or similar
        # We'll use a broad selector to be safe.
        potential_rows = soup.find_all(['div', 'tr'])
        
        for row in potential_rows:
            text = row.get_text(" | ", strip=True)
            
            # Filter 1: Must be a Carla Madison class
            if "Carla Madison" in text:
                # Filter 2: Must contain "FIT" (Redundancy check)
                if "FIT" in text.upper():
                    
                    # Regex Magic to extract the Class Name
                    # Looks for "FIT:" followed by text
                    name_match = re.search(r"FIT:?\s*([^|]+)", text, re.IGNORECASE)
                    class_name = name_match.group(1).strip() if name_match else "Unknown Class"
                    
                    # Attempt to find Date/Time patterns (e.g., "Mon, Feb 14")
                    # This is tricky without strict HTML, so we store the raw text for the dashboard to parse or display
                    
                    # Deduplication: Search results often duplicate the same card. 
                    # We check if we already added this class name.
                    if not any(d['Name'] == class_name for d in classes_data):
                        
                        # Simple Categorization
                        category = "Strength"
                        if any(x in class_name.upper() for x in ["YOGA", "PILATES"]): category = "Yoga"
                        elif any(x in class_name.upper() for x in ["CYCLE", "HIIT", "ZUMBA"]): category = "Cardio"
                        elif "AQUA" in class_name.upper(): category = "Water"

                        classes_data.append({
                            "Gym": "Carla Madison",
                            "Name": class_name,
                            "Day": "See App", # Placeholder until we confirm regex works
                            "FullDate": "Upcoming", 
                            "Time": "Check Sched",
                            "Type": category,
                            "Difficulty": "Open"
                        })
                        print(f"✅ Found: {class_name}")

    except Exception as e:
        print(f"❌ Error: {e}")
        classes_data.append({"Gym": "ERROR", "Name": str(e), "Type": "Error"})
        
    finally:
        driver.quit()
        
    # Force CSV Update
    if not classes_data:
        classes_data.append({
            "Gym": "Carla Madison", 
            "Name": "No Classes Detected (Check Script)", 
            "Day": datetime.now().strftime("%H:%M"), 
            "Type": "Strength"
        })
        
    return classes_data

if __name__ == "__main__":
    data = scrape_schedule()
    df = pd.DataFrame(data)
    df.to_csv("fitness_schedule.csv", index=False)
    print("disk update complete")
