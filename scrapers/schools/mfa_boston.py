"""Scraper for Museum of Fine Arts, Boston."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class MFABostonScraper(BaseScraper):
    school_id = "mfa-boston"
    exhibitions_url = "https://www.mfa.org/exhibitions"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_urls = set()

        # MFA uses Drupal. Exhibition titles in h2 tags with links to /exhibition/slug.
        # Each h2 is inside a parent div with an image and date text.
        h2s = soup.find_all("h2")

        for h2 in h2s:
            link = h2.find("a", href=True)
            if not link:
                continue

            href = link.get("href", "")
            # Only exhibition pages, skip /gallery/ (permanent collection)
            if "/exhibition/" not in href:
                continue

            if href in seen_urls:
                continue
            seen_urls.add(href)

            url = href
            if not url.startswith("http"):
                url = f"https://www.mfa.org{url}"

            # Title: the h2 text may contain a subtitle run together
            # e.g. "Subvert, Repair, ReclaimContemporary Artists Take ..."
            # Split on CamelCase boundary where lowercase meets uppercase
            raw_title = h2.get_text(strip=True)
            # Try to split subtitle: look for [lowercase][Uppercase] boundary
            parts = re.split(r"(?<=[a-z])(?=[A-Z])", raw_title, maxsplit=1)
            title = parts[0].strip() if parts else raw_title

            # Image
            parent = h2.find_parent(["div", "article", "li"])
            image_url = None
            if parent:
                img = parent.find("img")
                if img:
                    src = img.get("data-src") or img.get("src", "")
                    if not src.startswith("data:"):
                        image_url = src

            # Dates: look for date text in parent
            start_date, end_date = None, None
            if parent:
                for el in parent.find_all(["p", "span", "div", "time"]):
                    el_text = el.get_text(strip=True)
                    if re.search(r"(Through|Ongoing|January|February|March|April|May|June|July|August|September|October|November|December)", el_text):
                        start_date, end_date = self.parse_date_range(el_text)
                        if start_date or end_date:
                            break

            exhibitions.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
