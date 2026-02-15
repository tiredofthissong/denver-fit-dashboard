#!/bin/bash
# ===========================================
# Denver Fit Dashboard - Restructure Script
# ===========================================
# Run this from your project root folder:
#   chmod +x setup_new_structure.sh
#   ./setup_new_structure.sh
# ===========================================

set -e  # Exit on any error

echo "🚀 Starting repo restructure..."
echo ""

# -----------------------------
# 1. Create new folder structure
# -----------------------------
echo "📁 Creating folders..."
mkdir -p src/scraper
mkdir -p src/dashboard
mkdir -p data
mkdir -p scripts
mkdir -p tests
mkdir -p .github/workflows

echo "   ✓ Folders created"

# -----------------------------
# 2. Create src/scraper/__init__.py
# -----------------------------
echo "📝 Creating Python package files..."

cat > src/scraper/__init__.py << 'EOF'
"""Denver Fit Dashboard — Scraper Package"""
EOF

# -----------------------------
# 3. Create src/scraper/config.py
# -----------------------------
cat > src/scraper/config.py << 'EOF'
"""
Scraper configuration — URLs, selectors, timeouts.
"""

SCRAPER_CONFIG = {
    "base_url": "https://anc.apm.activecommunities.com/denver/activity/search",
    "search_params": {
        "onlineSiteId": "0",
        "activity_select_param": "2",
        "activity_keyword": "Carla Madison",
        "viewMode": "list",
    },
    "user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "page_load_timeout": 60,
    "post_load_delay": 5,
    "selectors": {
        "schedule_table": "table.activity-list, table[class*='schedule']",
        "schedule_row": "tr[data-activity-id], tbody tr",
        "fallback_row": "tr",
    },
    "max_retries": 3,
    "retry_delay": 10,
}


def build_url() -> str:
    from urllib.parse import urlencode
    params = urlencode(SCRAPER_CONFIG["search_params"])
    return f"{SCRAPER_CONFIG['base_url']}?{params}"
EOF

# -----------------------------
# 4. Create src/scraper/fetcher.py
# -----------------------------
cat > src/scraper/fetcher.py << 'EOF'
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
EOF

# -----------------------------
# 5. Create src/scraper/parser.py
# -----------------------------
cat > src/scraper/parser.py << 'EOF'
"""
Schedule parser — extracts structured data from HTML.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@dataclass
class FitnessClass:
    name: str
    date: str
    time: str
    location: str
    category: Optional[str] = None
    activity_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class ScheduleParser:
    CATEGORY_PATTERNS = {
        "yoga": r"\byoga\b",
        "spin": r"\b(spin|cycling|cycle)\b",
        "strength": r"\b(strength|weight|lift|barbell)\b",
        "cardio": r"\b(cardio|hiit|bootcamp|aerobic)\b",
        "aqua": r"\b(swim|aqua|pool|water)\b",
        "dance": r"\b(dance|zumba|barre)\b",
        "mind_body": r"\b(pilates|tai chi|meditation|stretch)\b",
    }

    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "html.parser")
        self.classes: list[FitnessClass] = []

    def parse(self) -> list[dict]:
        self.classes = (
            self._parse_table_rows() or
            self._parse_data_attributes() or
            []
        )

        if not self.classes:
            logger.warning("No classes found")

        return [c.to_dict() for c in self.classes]

    def _parse_table_rows(self) -> Optional[list[FitnessClass]]:
        tables = self.soup.find_all("table")
        if not tables:
            return None

        classes = []
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 3:
                    cls = self._parse_table_row(cols)
                    if cls:
                        classes.append(cls)

        return classes if classes else None

    def _parse_table_row(self, cols) -> Optional[FitnessClass]:
        texts = [col.get_text(strip=True) for col in cols]

        if not texts[0] or texts[0].lower() in ("name", "class", "activity"):
            return None

        name = texts[0]
        date = texts[1] if len(texts) > 1 else ""
        time_str = texts[2] if len(texts) > 2 else ""
        location = texts[3] if len(texts) > 3 else "Carla Madison Rec Center"

        return FitnessClass(
            name=name,
            date=date,
            time=time_str,
            location=location,
            category=self._detect_category(name),
        )

    def _parse_data_attributes(self) -> Optional[list[FitnessClass]]:
        rows = self.soup.select("[data-activity-id]")
        if not rows:
            return None

        classes = []
        for row in rows:
            cls = FitnessClass(
                name=self._extract_text(row, "[class*='name']"),
                date=self._extract_text(row, "[class*='date']"),
                time=self._extract_text(row, "[class*='time']"),
                location=self._extract_text(row, "[class*='location']") or "Carla Madison Rec Center",
                activity_id=row.get("data-activity-id"),
            )
            if cls.name:
                cls.category = self._detect_category(cls.name)
                classes.append(cls)

        return classes if classes else None

    def _extract_text(self, parent, selector: str) -> str:
        el = parent.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def _detect_category(self, name: str) -> str:
        name_lower = name.lower()
        for category, pattern in self.CATEGORY_PATTERNS.items():
            if re.search(pattern, name_lower, re.IGNORECASE):
                return category
        return "general"
EOF

# -----------------------------
# 6. Create scripts/run_scrape.py
# -----------------------------
cat > scripts/run_scrape.py << 'EOF'
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
EOF

chmod +x scripts/run_scrape.py

# -----------------------------
# 7. Create new GitHub workflow
# -----------------------------
echo "📝 Creating GitHub workflow..."

cat > .github/workflows/scrape.yml << 'EOF'
name: Scrape Schedule

on:
  schedule:
    - cron: "0 12 * * *"
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Chrome
        uses: browser-actions/setup-chrome@v1

      - name: Install ChromeDriver
        uses: nanasess/setup-chromedriver@v2

      - name: Install dependencies
        run: pip install selenium beautifulsoup4

      - name: Run scraper
        run: |
          Xvfb :99 -screen 0 1920x1080x24 &
          export DISPLAY=:99
          python scripts/run_scrape.py

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/schedule.json
          git diff --staged --quiet || git commit -m "Update schedule"
          git push
EOF

# -----------------------------
# 8. Move existing schedule.json
# -----------------------------
echo "📦 Moving existing files..."

if [ -f "schedule.json" ]; then
    mv schedule.json data/schedule.json
    echo "   ✓ Moved schedule.json to data/"
fi

# -----------------------------
# 9. Create new dashboard
# -----------------------------
echo "📝 Creating improved dashboard..."

cat > src/dashboard/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#0a0a0a">
  <title>CarlaFit</title>
  <style>
    :root {
      --bg: #0a0a0a;
      --card: #1a1a1a;
      --text: #f5f5f5;
      --muted: #888;
      --accent: #4ade80;
      --yoga: #a78bfa;
      --spin: #f472b6;
      --strength: #fb923c;
      --cardio: #f87171;
      --aqua: #38bdf8;
      --dance: #facc15;
      --general: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 1rem;
    }
    header {
      max-width: 600px;
      margin: 0 auto 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    h1 { font-size: 1.25rem; }
    .toggle {
      display: flex;
      gap: 0.25rem;
      background: var(--card);
      padding: 0.25rem;
      border-radius: 8px;
    }
    .toggle button {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.875rem;
    }
    .toggle button.active {
      background: var(--accent);
      color: var(--bg);
    }
    main {
      max-width: 600px;
      margin: 0 auto;
    }
    .loading, .empty, .error {
      text-align: center;
      padding: 3rem 1rem;
      color: var(--muted);
    }
    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid var(--card);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 1rem;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .day-header {
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--muted);
      margin: 1.5rem 0 0.5rem;
    }
    .card {
      background: var(--card);
      border-radius: 10px;
      padding: 0.875rem 1rem;
      margin-bottom: 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .info { flex: 1; min-width: 0; }
    .name {
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .meta { font-size: 0.8rem; color: var(--muted); }
    .time {
      font-weight: 600;
      font-size: 0.875rem;
      color: var(--accent);
    }
    .cat-yoga { background: var(--yoga); }
    .cat-spin { background: var(--spin); }
    .cat-strength { background: var(--strength); }
    .cat-cardio { background: var(--cardio); }
    .cat-aqua { background: var(--aqua); }
    .cat-dance { background: var(--dance); }
    .cat-general { background: var(--general); }
    footer {
      max-width: 600px;
      margin: 2rem auto 0;
      text-align: center;
      font-size: 0.7rem;
      color: var(--muted);
    }
  </style>
</head>
<body>

<header>
  <h1>💪 CarlaFit</h1>
  <div class="toggle">
    <button id="todayBtn" class="active">Today</button>
    <button id="weekBtn">Week</button>
  </div>
</header>

<main id="app">
  <div class="loading">
    <div class="spinner"></div>
    <p>Loading...</p>
  </div>
</main>

<footer id="footer"></footer>

<script>
let classes = [];
let view = "today";

async function load() {
  try {
    const r = await fetch("data/schedule.json", {cache:"no-store"});
    const d = await r.json();
    classes = d.classes || [];
    document.getElementById("footer").textContent = "Updated " + timeAgo(d.last_updated);
    render();
  } catch(e) {
    document.getElementById("app").innerHTML = '<div class="error">Failed to load</div>';
  }
}

function render() {
  const app = document.getElementById("app");
  if (!classes.length) {
    app.innerHTML = '<div class="empty">No classes</div>';
    return;
  }
  
  const now = new Date();
  const filtered = classes.filter(c => {
    const d = new Date(c.date);
    if (view === "today") return d.toDateString() === now.toDateString();
    const week = new Date(now); week.setDate(week.getDate() + 7);
    return d >= now && d <= week;
  });
  
  if (!filtered.length) {
    app.innerHTML = `<div class="empty">No classes ${view === "today" ? "today" : "this week"}</div>`;
    return;
  }
  
  const grouped = filtered.reduce((a, c) => {
    (a[c.date] = a[c.date] || []).push(c);
    return a;
  }, {});
  
  app.innerHTML = Object.entries(grouped).map(([date, items]) => `
    <div class="day-header">${formatDate(date)}</div>
    ${items.map(c => `
      <div class="card">
        <div class="dot cat-${c.category || 'general'}"></div>
        <div class="info">
          <div class="name">${c.name}</div>
          <div class="meta">${c.location || 'Carla Madison'}</div>
        </div>
        <div class="time">${c.time}</div>
      </div>
    `).join("")}
  `).join("");
}

function formatDate(s) {
  const d = new Date(s);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return "Today";
  const tom = new Date(now); tom.setDate(tom.getDate() + 1);
  if (d.toDateString() === tom.toDateString()) return "Tomorrow";
  return d.toLocaleDateString("en-US", {weekday:"short", month:"short", day:"numeric"});
}

function timeAgo(iso) {
  const mins = Math.floor((new Date() - new Date(iso)) / 60000);
  if (mins < 60) return mins + "m ago";
  if (mins < 1440) return Math.floor(mins/60) + "h ago";
  return Math.floor(mins/1440) + "d ago";
}

document.getElementById("todayBtn").onclick = () => {
  view = "today";
  document.getElementById("todayBtn").classList.add("active");
  document.getElementById("weekBtn").classList.remove("active");
  render();
};

document.getElementById("weekBtn").onclick = () => {
  view = "week";
  document.getElementById("weekBtn").classList.add("active");
  document.getElementById("todayBtn").classList.remove("active");
  render();
};

load();
</script>
</body>
</html>
HTMLEOF

# -----------------------------
# 10. Create root index.html redirect
# -----------------------------
cat > index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url=src/dashboard/index.html">
  <link rel="canonical" href="src/dashboard/index.html">
</head>
<body>
  <p>Redirecting to <a href="src/dashboard/index.html">dashboard</a>...</p>
</body>
</html>
EOF

# -----------------------------
# 11. Update requirements.txt
# -----------------------------
cat > requirements.txt << 'EOF'
selenium>=4.18.0
beautifulsoup4>=4.12.0
EOF

# -----------------------------
# 12. Clean up old files
# -----------------------------
echo "🧹 Cleaning up old files..."

# Remove duplicate workflow folder
if [ -d "workflows" ]; then
    rm -rf workflows
    echo "   ✓ Removed workflows/ (duplicate)"
fi

# Remove old scrape files
[ -f "scrape.py" ] && rm scrape.py && echo "   ✓ Removed old scrape.py"
[ -f "scrape_debug.py" ] && rm scrape_debug.py && echo "   ✓ Removed scrape_debug.py"
[ -f "fitness_schedule.csv" ] && rm fitness_schedule.csv && echo "   ✓ Removed fitness_schedule.csv"

# Remove old workflow
[ -f ".github/workflows/daily_scrape.yml" ] && rm .github/workflows/daily_scrape.yml && echo "   ✓ Removed old workflow"

# -----------------------------
# Done!
# -----------------------------
echo ""
echo "============================================"
echo "✅ RESTRUCTURE COMPLETE!"
echo "============================================"
echo ""
echo "New structure:"
echo "  src/scraper/     - Python scraper modules"
echo "  src/dashboard/   - Frontend HTML"
echo "  scripts/         - CLI entrypoints"
echo "  data/            - JSON output"
echo "  .github/workflows/ - GitHub Actions"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit: git add -A && git commit -m 'Restructure repo'"
echo "  3. Push: git push"
echo "  4. Test workflow: Go to GitHub → Actions → Run workflow"
echo ""
