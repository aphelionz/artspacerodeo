"""Scraper for Farnsworth Art Museum."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class FarnsworthScraper(BaseScraper):
    school_id = "farnsworth"
    exhibitions_url = "https://www.farnsworthmuseum.org/exhibitions/"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_urls = set()

        # Farnsworth lists exhibitions as links to /exhibition/slug/
        links = soup.find_all("a", href=lambda h: h and "/exhibition/" in h)

        for link in links:
            href = link.get("href", "")
            if href in seen_urls:
                continue
            seen_urls.add(href)

            url = href
            if not url.startswith("http"):
                url = f"https://www.farnsworthmuseum.org{url}"

            # The link text contains title + date run together
            # e.g. "Benjamin Spalding: Go Bang! | Momentum 2026Through September 20, 2026"
            full_text = link.get_text(strip=True)

            # Split title from date — look for "Through", "January", "February", etc.
            date_pattern = r"(Through\s|January|February|March|April|May|June|July|August|September|October|November|December)"
            m = re.search(date_pattern, full_text)
            if m:
                title = full_text[:m.start()].strip()
                date_text = full_text[m.start():].strip()
                start_date, end_date = self.parse_date_range(date_text)
            else:
                title = full_text
                start_date, end_date = None, None

            # Image: check parent container
            parent = link.find_parent(["div", "article", "li"])
            image_url = None
            if parent:
                img = parent.find("img")
                image_url = self.get_img_url(img, "https://www.farnsworthmuseum.org")

            if not title or len(title) < 3:
                continue

            exhibitions.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
