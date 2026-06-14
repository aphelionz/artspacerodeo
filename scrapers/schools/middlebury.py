"""Scraper for Middlebury College Museum of Art."""

import re

from scrapers.base import BaseScraper


class MiddleburyScraper(BaseScraper):
    school_id = "middlebury"
    exhibitions_url = "https://www.middlebury.edu/museum/exhibitions"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []

        # Look for exhibition listings with headings and links
        for heading in soup.select("h3 a, h2 a"):
            href = heading.get("href", "")
            title = heading.get_text(strip=True)
            if not title:
                continue

            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"https://www.middlebury.edu{href}"
            else:
                url = f"https://www.middlebury.edu/museum/exhibitions/{href}"

            container = heading.find_parent(["div", "article", "li", "section"])
            start, end = None, None
            image_url = None
            description = None

            if container:
                img = container.select_one("img")
                if img:
                    src = img.get("src") or img.get("data-src", "")
                    if src and not src.startswith("http"):
                        src = f"https://www.middlebury.edu{src}"
                    image_url = src or None

                text = container.get_text(" ", strip=True)
                date_match = re.search(
                    r"(\w+ \d{1,2})\s*[-–—]\s*(\w+ \d{1,2},?\s*\d{4})",
                    text,
                )
                if date_match:
                    date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                    start, end = self.parse_date_range(date_str)

                for p in container.select("p"):
                    p_text = p.get_text(strip=True)
                    if p_text and p_text != title and len(p_text) > 20:
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
