"""Scraper for Institute of Contemporary Art, Boston."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class ICABostonScraper(BaseScraper):
    school_id = "ica-boston"
    exhibitions_url = "https://www.icaboston.org/exhibitions"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_urls = set()

        # ICA uses WordPress with custom exhibition blocks.
        # Individual exhibitions appear as div.node-exhibition or via h3.teaser-title.
        # Each has a link to /exhibitions/slug/, date text, and sometimes an image.

        # Use the node-exhibition divs which have clean structure
        nodes = soup.select("div.node-exhibition")

        for node in nodes:
            title_el = node.find(["h2", "h3"])
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Link
            link = node.find("a", href=lambda h: h and "/exhibitions/" in h)
            if not link:
                continue

            url = link.get("href", "")
            if not url.startswith("http"):
                url = f"https://www.icaboston.org{url}"

            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Image
            img = node.find("img")
            image_url = None
            if img:
                src = img.get("data-src") or img.get("src", "")
                if not src.startswith("data:"):
                    image_url = src

            # Dates: text like "Feb 12 – Aug 2, 2026" in the node
            start_date, end_date = None, None
            node_text = node.get_text(" ", strip=True)
            # Remove title from text to find date portion
            date_text = node_text.replace(title, "").strip()
            if date_text:
                # Normalize dashes
                date_text = date_text.replace("–", "-").replace("—", "-")
                start_date, end_date = self.parse_date_range(date_text)

            exhibitions.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
