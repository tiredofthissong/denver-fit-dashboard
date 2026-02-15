#!/usr/bin/env python3
"""
Denver Fit Dashboard — Schedule Scraper
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.config import build_url, SCRAPER_CONFIG
from src.scraper.fetcher import ScheduleFetcher
from src.scraper.parser import ScheduleParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "schedule.json"


def scrape_schedule(retries: int = 3) -> list[dict]:
    url = build_url()
    last_error = None

    for attempt in range(1, retries + 1):
        logger.info(f"Attempt {attempt}/{retries}")

        try:
            with ScheduleFetcher(headless=True) as fetcher:
                html = fetcher.fetch(
                    url=url,
                    wait_selector=SCRAPER_CONFIG["selectors"]["fallback_row"],
                    timeout=SCRAPER_CONFIG["page_load_timeout"],
                )

            parser = ScheduleParser(html)
            classes = parser.parse()

            if classes:
                logger.info(f"Scraped {len(classes)} classes")
                return classes
            else:
                logger.warning("No classes found")

        except Exception as e:
            last_error = e
            logger.error(f"Attempt {attempt} failed: {e}")

            if attempt < retries:
                delay = SCRAPER_CONFIG["retry_delay"] * attempt
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)

    logger.error(f"All attempts failed: {last_error}")
    return []


def save_schedule(classes: list[dict]):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "class_count": len(classes),
        "classes": classes,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved to {OUTPUT_FILE}")


def main():
    logger.info("Starting scrape...")
    classes = scrape_schedule()
    save_schedule(classes)

    if not classes:
        sys.exit(1)


if __name__ == "__main__":
    main()
