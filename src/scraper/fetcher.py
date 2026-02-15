"""
Browser-based fetcher for JS-rendered schedule pages.
"""

import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import SCRAPER_CONFIG

logger = logging.getLogger(__name__)


class ScheduleFetcher:
    """Handles browser automation for fetching schedule data."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        opts = Options()

        if self.headless:
            opts.add_argument("--headless=new")

        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-agent={SCRAPER_CONFIG['user_agent']}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=opts)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def fetch(self, url: str, wait_selector: str = "tr", timeout: int = 60) -> str:
        self.driver = self._create_driver()

        try:
            logger.info(f"Loading: {url}")
            self.driver.get(url)

            logger.info(f"Waiting for '{wait_selector}' (timeout: {timeout}s)")
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
            )

            time.sleep(SCRAPER_CONFIG["post_load_delay"])
            return self.driver.page_source

        finally:
            self.close()

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
