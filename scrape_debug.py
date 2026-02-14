"""Debug scraper - Aligned with Production Logic"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

TARGET_URL = "https://anc.apm.activecommunities.com/denver/activity/search?onlineSiteId=0&activity_select_param=2&activity_keyword=Carla%20Madison&viewMode=list"

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    # MATCHING PRODUCTION: Add Real User Agent
    opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=opts)

print("Starting debug scraper...")
driver = setup_driver()

try:
    print(f"Loading: {TARGET_URL}")
    driver.get(TARGET_URL)

    # MATCHING PRODUCTION: Smart Wait for Table Rows (tr)
    print("Waiting up to 60s for table rows...")
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.TAG_NAME, "tr"))
        )
        print("✓ Element detected! Buffer wait (10s)...")
        time.sleep(10)
    except Exception as e:
        print(f"✗ Timeout detected: {e}")

    # Save screenshot
    driver.save_screenshot("debug_screenshot.png")
    print("✓ Screenshot saved")

    # Save HTML source
    with open("debug_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("✓ HTML source saved")

    # Parse and show what we find
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 1. Check for Table Rows (The Main Script's Target)
    rows = soup.find_all("tr")
    print(f"\n[CRITICAL] Total Table Rows (tr) found: {len(rows)}")

    # 2. Check for Carla Madison Text
    body_text = soup.get_text()
    if "Carla Madison" in body_text:
        print("✓ 'Carla Madison' found in text")
    else:
        print("✗ 'Carla Madison' NOT found in text")

    # 3. Sample Data Extraction
    print(f"\n--- First 5 Rows Content ---")
    for i, row in enumerate(rows[:5], 1):
        text = row.get_text(" | ", strip=True)[:100]
        print(f"Row {i}: {text}...")

finally:
    driver.quit()

print("\n✓ Debug complete. Check debug_source.html and debug_screenshot.png")
