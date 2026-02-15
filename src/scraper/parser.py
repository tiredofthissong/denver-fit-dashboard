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
