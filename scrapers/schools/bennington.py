"""Scraper for Bennington Museum."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BenningtonScraper(BaseScraper):
    school_id = "bennington"
    exhibitions_url = "https://benningtonmuseum.org/whats-on-view/special-exhibitions/"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_titles = set()

        # Bennington uses WordPress portfolio items. Exhibition titles in h2 tags
        # with links to /portfolio-items/slug/?portfolioCats=67
        h2s = soup.find_all("h2")

        for h2 in h2s:
            text = h2.get_text(strip=True)
            if not text or len(text) < 4:
                continue

            # Skip page headings
            if text.lower() in ("special exhibitions",):
                continue

            if text in seen_titles:
                continue
            seen_titles.add(text)

            # Get link if present
            link = h2.find("a", href=True)
            url = link.get("href", "") if link else self.exhibitions_url
            if url and not url.startswith("http"):
                url = f"https://benningtonmuseum.org{url}"

            # Look for dates in parent container text
            parent = h2.find_parent(["div", "article", "section"])
            start_date, end_date = None, None
            description = None
            if parent:
                parent_text = parent.get_text(" ", strip=True)
                # Look for date ranges like "April 2 - May 17, 2026"
                date_match = re.search(
                    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                    r"\s+\d{1,2}[\s,\-–—]+.*?\d{4}",
                    parent_text,
                )
                if date_match:
                    start_date, end_date = self.parse_date_range(date_match.group(0))

            # Image: check parent and article containers
            image_url = None
            article = h2.find_parent("article")
            if article:
                img = article.find("img")
                image_url = self.get_img_url(img, "https://benningtonmuseum.org")
            if not image_url and parent:
                img = parent.find("img")
                image_url = self.get_img_url(img, "https://benningtonmuseum.org")

            exhibitions.append({
                "title": text,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
