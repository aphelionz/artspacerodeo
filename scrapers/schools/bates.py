"""Scraper for Bates College Museum of Art."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BatesScraper(BaseScraper):
    school_id = "bates"
    exhibitions_url = "https://www.bates.edu/museum/exhibitions/"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []

        # Bates exhibition pages live at /museum/EXHIBITION-SLUG/
        # The exhibitions page has sections for current and upcoming shows.
        # Look for image+text cards that link to exhibition detail pages.
        # Key insight: real exhibition links have images alongside them.

        # Find all figure/media-text blocks or containers that have both an image and a link
        for container in soup.select(".wp-block-media-text, .wp-block-group, .wp-block-columns, article, figure"):
            img = container.select_one("img")
            link = container.select_one("a[href*='/museum/']")
            if not link:
                continue

            href = link.get("href", "")
            # Must be a direct child page of /museum/
            if not re.search(r"/museum/[a-z][\w-]+/?$", href):
                continue
            if href.rstrip("/").endswith(("/museum", "/museum/exhibitions")):
                continue

            # Get title from heading or link text
            heading = container.select_one("h2, h3, h4")
            title = heading.get_text(strip=True) if heading else link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            image_url = img.get("src") or img.get("data-src") if img else None
            url = href if href.startswith("http") else f"https://www.bates.edu{href}"

            # Look for date text
            text = container.get_text(" ", strip=True)
            start, end = None, None
            date_match = re.search(
                r"(\w+ \d{1,2})\s*[-–—]\s*(\w+ \d{1,2},?\s*\d{4})",
                text,
            )
            if date_match:
                date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                start, end = self.parse_date_range(date_str)

            exhibitions.append({
                "title": title,
                "start_date": start,
                "end_date": end,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        # Deduplicate by URL
        seen = set()
        unique = []
        for ex in exhibitions:
            if ex["url"] not in seen:
                seen.add(ex["url"])
                unique.append(ex)

        return unique
