"""Scraper for MassArt (Massachusetts College of Art and Design)."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper

SKIP_TITLES = {
    "exhibitions", "visit maam", "visit maam(opens in new tab)",
    "learn more", "view all", "about", "visit", "support",
}


class MassArtScraper(BaseScraper):
    school_id = "massart"
    exhibitions_url = "https://massart.edu/exhibitions"

    def scrape(self):
        exhibitions = []

        # Try main MassArt exhibitions page
        try:
            soup = self.fetch(self.exhibitions_url)
            exhibitions.extend(self._parse_page(soup, "https://massart.edu"))
        except Exception as e:
            print(f"  [{self.school_id}] main site error: {e}")

        # Also try MAAM (MassArt Art Museum)
        try:
            maam_soup = self.fetch("https://maam.massart.edu/exhibitions")
            exhibitions.extend(self._parse_page(maam_soup, "https://maam.massart.edu"))
        except Exception as e:
            print(f"  [{self.school_id}] MAAM error: {e}")

        # Deduplicate by title
        seen = set()
        unique = []
        for ex in exhibitions:
            if ex["title"] not in seen:
                seen.add(ex["title"])
                unique.append(ex)

        return unique

    def _parse_page(self, soup, base_url):
        results = []

        for link in soup.select("a[href*='exhibition']"):
            href = link.get("href", "")
            if href.rstrip("/") in ("#", "/exhibitions", ""):
                continue
            # Skip filter/query links and past exhibition links
            if "?" in href or "/past" in href:
                continue

            title_el = link.select_one("h2, h3, h4, .title")
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
            if not title or len(title) < 3 or len(title) > 200:
                continue
            if title.lower().strip().rstrip("(opens in new tab)") in SKIP_TITLES:
                continue
            if title.lower() in SKIP_TITLES:
                continue

            img = link.select_one("img")
            image_url = self.get_img_url(img, base_url)
            # Image may be in parent article/card container, not inside the link
            if not image_url:
                parent = link.find_parent(["article", "div", "section"])
                if parent:
                    pimg = parent.find("img")
                    image_url = self.get_img_url(pimg, base_url)

            url = href if href.startswith("http") else f"{base_url}{href}"

            container = link.find_parent(["div", "section", "article"]) or link
            text = container.get_text(" ", strip=True)
            start, end = None, None
            date_match = re.search(
                r"(\w+ \d{1,2})\s*[-–—]\s*(\w+ \d{1,2},?\s*\d{4})",
                text,
            )
            if date_match:
                date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                start, end = self.parse_date_range(date_str)

            results.append({
                "title": title,
                "start_date": start,
                "end_date": end,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return results
