"""Debug scraper - saves HTML to inspect actual structure"""
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
    return webdriver.Chrome(options=opts)

print("Starting debug scraper...")
driver = setup_driver()

try:
    driver.get(TARGET_URL)
    print("Page loaded, waiting 8 seconds...")
    time.sleep(8)

    # Save screenshot
    driver.save_screenshot("debug_screenshot.png")
    print("✓ Screenshot saved")

    # Save HTML source
    with open("debug_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("✓ HTML source saved")

    # Parse and show what we find
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Find all links
    all_links = soup.find_all("a", href=True)
    print(f"\nTotal links found: {len(all_links)}")

    # Show first 10 activity-related links
    activity_links = [l for l in all_links if "activity" in l.get("href", "").lower()][:10]
    print(f"\nFirst 10 activity links:")
    for i, link in enumerate(activity_links, 1):
        href = link.get("href", "")
        text = link.get_text(strip=True)[:60]
        print(f"{i}. {text}")
        print(f"   URL: {href}\n")

    # Check for results count
    results_text = soup.get_text()
    if "carla madison" in results_text.lower():
        print("✓ 'Carla Madison' found in page text")
    else:
        print("✗ 'Carla Madison' NOT found in page text")

    # Find any text mentioning classes/activities
    if "fit" in results_text.lower():
        print("✓ 'FIT' found in page text")

finally:
    driver.quit()

print("\n✓ Debug complete. Check debug_source.html and debug_screenshot.png")
