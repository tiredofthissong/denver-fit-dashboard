import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Pivot: We are using the SEARCH page instead of the Calendar.
# We search for "FIT" and ask for the "List View" directly.
TARGET_URL = "https://anc.apm.activecommunities.com/denver/activity/search?onlineSiteId=0&activity_select_param=2&activity_keyword=FIT&viewMode=list"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_schedule():
    print("🚀 Starting Search-Based Extraction...")
    driver = setup_driver()
    classes_data = []
    
    try:
        driver.get(TARGET_URL)
        print("🔗 Search Page Loaded. Waiting for Results Table...")
        
        # Wait for the result table (class usually contains 'table' or 'grid')
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "tbody"))
        )
        time.sleep(5) # Buffer for list to fully render
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # ActiveNet Search Results are usually in a standard table
        rows = soup.select("tbody tr")
        print(f"👀 Found {len(rows)} potential classes.")

        for row in rows:
            # We need to find the specific columns. 
            # Usually: Name | Date | Time | Location is buried in text
            text_content = row.get_text(" | ", strip=True)
            
            # --- FILTER: CARLA MADISON ONLY ---
            # We filter here because the URL searches ALL Denver gyms
            if "Carla Madison" in text_content:
                
                # Extracting details from the text blob
                # Format is often: "Activity Name | Number | ... | Date | Time | ... | Location"
                # This is "Fuzzy Extraction" because columns change.
                
                parts = text_content.split("|")
                
                # Basic cleaner
                name = parts[0].strip().replace("FIT:", "").strip()
                
                # Find the part that looks like a date/time
                # We'll just grab the whole string for now to ensure we get data
                # You can refine this logic once we see the first successful CSV
                
                # Categorize
                category = "Strength"
                if any(x in name.upper() for x in ["YOGA", "PILATES"]): category = "Yoga"
                elif any(x in name.upper() for x in ["CYCLE", "ZUMBA", "HIIT"]): category = "Cardio"
                elif "AQUA" in name.upper(): category = "Water"

                classes_data.append({
                    "Gym": "Carla Madison",
                    "Name": name,
                    "Day": "Upcoming", # Placeholder
                    "FullDate": text_content, # Storing full text so you can debug what the robot sees
                    "Time": "Check App",
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
        df = pd.DataFrame([{
            "Gym": "Carla Madison", "Name": "No Classes Found (Search Mode)", 
            "Day": "Today", "FullDate": "Today", "Time": "00:00", 
            "Type": "Strength", "Difficulty": "Error"
        }])
    
    df.to_csv("fitness_schedule.csv", index=False)
    print(f"💾 Saved {len(data)} classes.")
