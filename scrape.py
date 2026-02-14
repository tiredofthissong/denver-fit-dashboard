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
# We are going back to the CALENDAR VIEW (List Mode) because it contains the most data.
TARGET_URL = "https://anc.apm.activecommunities.com/denver/calendars?onlineSiteId=0&defaultCalendarId=5&locationId=363&displayType=1&view=2"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    # mimicking a real user aggressively
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_schedule():
    driver = setup_driver()
    classes_data = []
    status_log = "Init"
    
    try:
        driver.get(TARGET_URL)
        # Wait for the specific list table
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "fc-list-table"))
            )
            status_log = "Table Found"
        except:
            status_log = "Table Timeout - Page Title: " + driver.title

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Strategy: Grab ANY row that looks like an event
        rows = soup.select(".fc-list-table tbody tr")
        
        if not rows:
            # Fallback: Check for 'Access Denied' or specific error text
            body_text = soup.get_text()[:200].replace("\n", " ")
            status_log += f" | Content Preview: {body_text}"

        current_date = "Upcoming"
        
        for row in rows:
            # Date Header
            if "fc-list-heading" in row.get("class", []):
                current_date = row.get_text(strip=True)
                continue
            
            # Event Row
            if "fc-list-item" in row.get("class", []):
                title = row.find("td", class_="fc-list-item-title").get_text(strip=True)
                time_val = row.find("td", class_="fc-list-item-time").get_text(strip=True)
                
                # Loose Filter: Grab everything to prove it works, filter "FIT" later
                # We save everything so we can see if the scraper is working AT ALL
                classes_data.append({
                    "Gym": "Carla Madison",
                    "Name": title,
                    "Day": current_date, 
                    "FullDate": current_date,
                    "Time": time_val,
                    "Type": "Raw Data",
                    "Difficulty": "Debug"
                })

    except Exception as e:
        status_log = f"Crash: {str(e)}"
        
    finally:
        driver.quit()
    
    # --- FORCE UPDATE LOGIC ---
    # If empty, add a row with the Status Log + Timestamp
    # This guarantees the file changes byte-for-byte, so Git will commit it.
    if not classes_data:
        classes_data.append({
            "Gym": "DEBUG", 
            "Name": f"Status: {status_log}", 
            "Day": datetime.now().strftime("%H:%M:%S"), 
            "FullDate": "Force Update", 
            "Time": "00:00", 
            "Type": "Error", 
            "Difficulty": "Fix Required"
        })
        
    return classes_data

if __name__ == "__main__":
    data = scrape_schedule()
    df = pd.DataFrame(data)
    df.to_csv("fitness_schedule.csv", index=False)
    print("disk update complete")
