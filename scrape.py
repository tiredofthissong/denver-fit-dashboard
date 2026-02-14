import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION ---
# We stick to the List View (displayType=1) as it is usually text-heavy
TARGET_URL = "https://anc.apm.activecommunities.com/denver/calendars?onlineSiteId=0&defaultCalendarId=5&locationId=363&displayType=1&view=2"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_schedule():
    print("🚀 Starting Robust Extraction...")
    driver = setup_driver()
    classes_data = []
    
    try:
        driver.get(TARGET_URL)
        print("🔗 Navigated to URL. Waiting for AJAX...")
        
        # Wait longer (20s) and specifically for the main container
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(10) # Aggressive wait for ActiveNet's slow spinner
        
        # --- DEBUG ARTIFACTS ---
        # We save these to check later if the CSV is still empty
        driver.save_screenshot("debug_screenshot.png")
        with open("debug_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("📸 Screenshot and HTML saved for debugging.")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # --- STRATEGY 1: The Standard Table ---
        rows = soup.select(".fc-list-table tbody tr")
        print(f"👀 Strategy 1 found {len(rows)} table rows.")

        # --- STRATEGY 2: Text Search (Fallback) ---
        if len(rows) == 0:
            print("⚠️ Table not found. Attempting Text Search...")
            # Find all elements containing "FIT:"
            fit_elements = soup.find_all(string=lambda text: text and "FIT:" in text)
            print(f"👀 Strategy 2 found {len(fit_elements)} text matches.")
            
            # If we found text matches but no table, we try to parse the match parent
            for text_node in fit_elements:
                event_name = text_node.strip().replace("FIT:", "").strip()
                # Default "Today" since we lost the date context in this fallback mode
                # This is just to prove we CAN see data
                classes_data.append({
                    "Gym": "Carla Madison",
                    "Name": event_name,
                    "Day": "Upcoming", 
                    "FullDate": "Check Link",
                    "Time": "Check Link",
                    "Type": "Strength" if "Total" in event_name else "Cardio",
                    "Difficulty": "Open"
                })

        # Process Strategy 1 Rows (Preferred)
        current_date = "Upcoming"
        for row in rows:
            # Check if this is a Date Header
            if "fc-list-heading" in row.get("class", []):
                date_cell = row.find("td", class_="fc-list-heading-main") or row.find("td")
                if date_cell:
                    current_date = date_cell.get_text(strip=True)
                continue
            
            # Check if this is an Event Item
            if "fc-list-item" in row.get("class", []):
                title_cell = row.find("td", class_="fc-list-item-title")
                time_cell = row.find("td", class_="fc-list-item-time")
                
                if title_cell:
                    title_text = title_cell.get_text(strip=True)
                    time_text = time_cell.get_text(strip=True) if time_cell else "N/A"
                    
                    if "FIT" in title_text.upper():
                        clean_name = title_text.replace("FIT:", "").replace("FIT", "").strip()
                        
                        # Categorize
                        category = "Strength"
                        if any(x in clean_name.upper() for x in ["YOGA", "PILATES", "STRETCH"]): category = "Yoga"
                        elif any(x in clean_name.upper() for x in ["CYCLE", "ZUMBA", "HIIT", "CARDIO", "KICK"]): category = "Cardio"
                        elif "AQUA" in clean_name.upper(): category = "Water"

                        classes_data.append({
                            "Gym": "Carla Madison",
                            "Name": clean_name,
                            "Day": current_date.split(',')[0] if ',' in current_date else current_date,
                            "FullDate": current_date,
                            "Time": time_text,
                            "Type": category,
                            "Difficulty": "Open"
                        })

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        
    finally:
        driver.quit()
        
    return classes_data

if __name__ == "__main__":
    data = scrape_schedule()
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # If empty, create dummy row so CSV isn't invalid
    if df.empty:
        print("⚠️ No classes found! Saving empty placeholder.")
        df = pd.DataFrame([{
            "Gym": "Carla Madison", "Name": "No Classes Found (Debug)", 
            "Day": "Today", "FullDate": "Today", "Time": "00:00", 
            "Type": "Strength", "Difficulty": "Error"
        }])
    
    df.to_csv("fitness_schedule.csv", index=False)
    print(f"💾 Schedule saved with {len(data)} classes.")
