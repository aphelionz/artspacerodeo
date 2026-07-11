"""Scraper for Bates College Museum of Art."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BatesScraper(BaseScraper):
    school_id = "bates"
    # The /museum/exhibitions/ page goes stale (it still listed a 2025 show
    # in July 2026); the homepage hover-board slider is what the museum
    # actually keeps current.
    exhibitions_url = "https://www.bates.edu/museum/"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []
        seen = set()

        # Current shows live in hover-board slides: a div with a
        # background-image style containing h2 (title), p (dates),
        # and a link to the exhibition page.
        for board in soup.select(".wp-block-bates-framework-hover-board"):
            heading = board.find(["h2", "h3"])
            link = board.find("a", href=re.compile(r"bates\.edu/museum/|^/museum/"))
            if not heading or not link:
                continue

            title = heading.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            href = link["href"]
            url = href if href.startswith("http") else f"https://www.bates.edu{href}"
            if url in seen:
                continue
            seen.add(url)

            image_url = None
            style = board.get("style", "")
            m = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style)
            if m:
                image_url = m.group(1)

            start, end = None, None
            date_p = board.find("p")
            if date_p:
                start, end = self.parse_date_range(date_p.get_text(strip=True))

            exhibitions.append({
                "title": title,
                "start_date": start,
                "end_date": end,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
