import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION ---
# We use the 'List View' (displayType=1) because it is much easier for a robot to read than a calendar grid.
# Location 363 = Carla Madison
TARGET_URL = "https://anc.apm.activecommunities.com/denver/calendars?onlineSiteId=0&defaultCalendarId=5&locationId=363&displayType=1&view=2"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Fool the site into thinking we are a real user
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_schedule():
    print("🚀 Starting Extraction...")
    driver = setup_driver()
    
    try:
        driver.get(TARGET_URL)
        # Wait up to 15 seconds for the calendar data to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fc-list-table"))
        )
        time.sleep(3) # Extra buffer for "AJAX" to settle
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        classes_data = []
        
        # In 'List View', ActiveNet uses a table with class 'fc-list-table'
        # We iterate through the rows.
        rows = soup.select(".fc-list-table tbody tr")
        
        current_date = ""
        
        for row in rows:
            # Header rows contain the date (e.g., "Monday, February 14, 2026")
            if "fc-list-heading" in row.get("class", []):
                current_date = row.find("td", class_="fc-list-heading-main").get_text(strip=True)
                continue
            
            # Event rows contain the class info
            if "fc-list-item" in row.get("class", []):
                time_cell = row.find("td", class_="fc-list-item-time")
                title_cell = row.find("td", class_="fc-list-item-title")
                
                time_text = time_cell.get_text(strip=True) if time_cell else "N/A"
                title_text = title_cell.get_text(strip=True) if title_cell else "Unknown"
                
                # --- FILTER PROTOCOL: ONLY "FIT" CLASSES ---
                if "FIT" in title_text.upper():
                    # Parse "FIT: Body Pump" -> "Body Pump"
                    clean_name = title_text.replace("FIT:", "").replace("FIT", "").strip()
                    
                    # Determine Category based on keywords
                    category = "Strength" # Default
                    if any(x in clean_name.upper() for x in ["YOGA", "PILATES", "STRETCH"]):
                        category = "Yoga"
                    elif any(x in clean_name.upper() for x in ["CYCLE", "ZUMBA", "HIIT", "CARDIO"]):
                        category = "Cardio"
                    elif "AQUA" in clean_name.upper():
                        category = "Water"

                    classes_data.append({
                        "Gym": "Carla Madison",
                        "Name": clean_name,
                        "Day": current_date.split(',')[0], # Just "Monday"
                        "FullDate": current_date,
                        "Time": time_text,
                        "Type": category,
                        "Difficulty": "Open" # Default
                    })
                    print(f"✅ Found: {clean_name} on {current_date}")

        return classes_data

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return []
        
    finally:
        driver.quit()

if __name__ == "__main__":
    data = scrape_schedule()
    
    # Save even if empty (updates the file timestamp)
    df = pd.DataFrame(data)
    # Ensure columns exist even if no data found
    if df.empty:
        df = pd.DataFrame(columns=["Gym", "Name", "Day", "FullDate", "Time", "Type", "Difficulty"])
        
    df.to_csv("fitness_schedule.csv", index=False)
    print("💾 Schedule saved to fitness_schedule.csv")
