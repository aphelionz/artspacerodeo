"""Scraper for Currier Museum of Art."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class CurrierScraper(BaseScraper):
    school_id = "currier"
    exhibitions_url = "https://www.currier.org/all-exhibitions"

    # Headings that are not exhibition titles
    SKIP_HEADINGS = {
        "membership", "archive", "museum", "discover", "upcoming shows",
        "join", "support", "visit", "current and upcoming", "exhibitions",
        "learn about", "on view",
    }

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_titles = set()

        # Currier is a Wix site. Exhibition info appears in h2 tags within sections.
        # The "Discover Something New" section has current exhibitions.
        # The "Upcoming shows" section has upcoming ones.
        # The "Archive" section should be skipped.

        in_archive = False

        for h2 in soup.find_all("h2"):
            text = h2.get_text(strip=True)
            if not text or len(text) < 4:
                continue

            text_lower = text.lower()

            # Check for archive section marker
            if "archive" in text_lower:
                in_archive = True
                continue
            if in_archive:
                continue

            # Skip non-exhibition headings
            if any(skip in text_lower for skip in self.SKIP_HEADINGS):
                continue

            # Skip if this looks like a subtitle/continuation of the previous h2
            # (e.g., the previous ended with ":" and this is the subtitle)
            prev_h2 = h2.find_previous("h2")
            if prev_h2:
                prev_text = prev_h2.get_text(strip=True)
                if prev_text.endswith(":"):
                    # This is a subtitle — skip it (we already combined it with the parent)
                    continue

            # If this h2 ends with ":", combine with next h2
            if text.endswith(":"):
                next_h2 = h2.find_next("h2")
                if next_h2:
                    text = f"{text} {next_h2.get_text(strip=True)}"

            # Deduplicate
            if text in seen_titles:
                continue
            seen_titles.add(text)

            # Try to find dates in nearby h3 elements
            start_date, end_date = None, None
            h3 = h2.find_next("h3")
            if h3:
                h3_text = h3.get_text(strip=True)
                # h3 contains things like "Scheier Gallery | Through April 12, 2026"
                date_match = re.search(
                    r"(Through\s|January|February|March|April|May|June|July|August|September|October|November|December)",
                    h3_text,
                )
                if date_match:
                    date_text = h3_text[date_match.start():]
                    start_date, end_date = self.parse_date_range(date_text)

            # Image: walk up ancestors for Wix wow-image elements
            image_url = None
            el = h2
            for _ in range(3):
                el = el.parent
                if not el:
                    break
                img = el.find("img")
                if img:
                    image_url = self.get_img_url(img, "https://www.currier.org")
                    if image_url:
                        break

            exhibitions.append({
                "title": text,
                "start_date": start_date,
                "end_date": end_date,
                "url": self.exhibitions_url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
