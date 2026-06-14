"""Scraper for Portland Museum of Art."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class PMAScraper(BaseScraper):
    school_id = "pma"
    exhibitions_url = "https://www.portlandmuseum.org/whats-on/"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []

        # PMA uses Kadence query blocks — each exhibition is an <li> with class kb-query-item
        items = soup.select("li.kb-query-item")

        for item in items:
            # Title + URL: the "Learn More" link points to /exhibitions/slug/
            link = item.find("a", href=True)
            if not link:
                continue
            url = link.get("href", "")
            if not url.startswith("http"):
                url = f"https://www.portlandmuseum.org{url}"

            # Title: get full item text, strip dates and "Learn More"
            dates_el = item.select_one(".exhibition-dates")
            dates_text = dates_el.get_text(strip=True) if dates_el else ""
            full_text = item.get_text(" ", strip=True)
            # Remove dates text and "Learn More"
            title = full_text
            if dates_text:
                title = title.replace(dates_text, "")
            title = re.sub(r"\s*Learn More\s*$", "", title).strip()

            if not title or len(title) < 3:
                continue

            # Image: handles lazy loading (data-lazy-src, data-src, srcset, etc.)
            img = item.find("img")
            image_url = self.get_img_url(img, "https://www.portlandmuseum.org")

            # Dates: .exhibition-dates contains text like "On view through June 7th"
            # or "On view July 3, 2026 through October 18, 2026"
            start_date, end_date = None, None
            if dates_text:
                # Strip "On view" prefix and ordinal suffixes
                clean = re.sub(r"(?i)^on view\s*", "", dates_text)
                clean = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", clean)
                start_date, end_date = self.parse_date_range(clean)

            exhibitions.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
