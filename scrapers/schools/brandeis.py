"""Scraper for Brandeis University Rose Art Museum."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BrandeisScraper(BaseScraper):
    school_id = "brandeis"
    exhibitions_url = "https://www.brandeis.edu/rose/exhibitions/index.html"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []

        # Rose Art Museum uses h3 headings for exhibition titles
        for heading in soup.select("h3"):
            link = heading.select_one("a")
            if link:
                title = link.get_text(strip=True)
                href = link.get("href", "")
            else:
                title = heading.get_text(strip=True)
                href = ""

            if not title:
                continue

            # Skip if title looks like a date (starts with month name + number)
            if re.match(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d", title):
                continue

            # Skip nav items
            if title.lower() in ("enhance your visit", "plan your visit", "past exhibitions"):
                continue

            # Build full URL
            if href:
                if href.startswith("http"):
                    url = href
                elif href.startswith("/"):
                    url = f"https://www.brandeis.edu{href}"
                else:
                    url = f"https://www.brandeis.edu/rose/exhibitions/{href}"
            else:
                url = self.exhibitions_url

            # Look for date and description in siblings/container
            container = heading.find_parent(["div", "section", "article", "li"])
            start, end = None, None
            description = None
            image_url = None

            if container:
                img = container.select_one("img")
                image_url = self.get_img_url(img, self.exhibitions_url)
                # Image may be in a sibling div (e.g. block__text vs block__img)
                if not image_url:
                    outer = container.find_parent(["div", "section", "article"])
                    if outer:
                        img = outer.find("img")
                        image_url = self.get_img_url(img, self.exhibitions_url)

                text = container.get_text(" ", strip=True)
                # Look for date pattern: "Month DD, YYYY - Month DD, YYYY"
                date_match = re.search(
                    r"(\w+ \d{1,2},?\s*\d{4})\s*[-–—]\s*(\w+ \d{1,2},?\s*\d{4})",
                    text,
                )
                if date_match:
                    date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                    start, end = self.parse_date_range(date_str)
                else:
                    date_match = re.search(
                        r"(\w+ \d{1,2})\s*[-–—]\s*(\w+ \d{1,2},?\s*\d{4})",
                        text,
                    )
                    if date_match:
                        date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                        start, end = self.parse_date_range(date_str)

                for p in container.select("p"):
                    p_text = p.get_text(strip=True)
                    if (
                        p_text
                        and p_text != title
                        and len(p_text) > 20
                        and not re.match(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d", p_text)
                    ):
                        description = p_text[:300]
                        break

            exhibitions.append({
                "title": title,
                "start_date": start,
                "end_date": end,
                "url": url,
                "image_url": image_url,
                "description": description,
            })

        return exhibitions
