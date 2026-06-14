"""Scraper for Bowdoin College Museum of Art."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BowdoinScraper(BaseScraper):
    school_id = "bowdoin"
    exhibitions_url = "https://www.bowdoin.edu/art-museum/exhibitions/"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []

        # Exhibition links are relative: href="2026/slug.html"
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            # Match relative year-prefixed links like "2026/creating-the-modern.html"
            if not re.match(r"^20\d{2}/", href):
                continue

            title_el = link.select_one("h4, h3, h2, strong, b")
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            img = link.select_one("img")
            image_url = self.get_img_url(img, self.exhibitions_url)
            # Image link and title link are separate <a> tags with same href.
            # If this link has no img, find sibling link with same href that does.
            if not image_url:
                for sibling_link in soup.select(f'a[href="{href}"]'):
                    sib_img = sibling_link.select_one("img")
                    if sib_img:
                        image_url = self.get_img_url(sib_img, self.exhibitions_url)
                        break

            url = f"https://www.bowdoin.edu/art-museum/exhibitions/{href}"

            # Date text — search link text, parent, and grandparent
            start, end = None, None
            for el in [link, link.parent, link.parent.parent if link.parent else None]:
                if not el:
                    continue
                text = el.get_text(" ", strip=True)
                # Try "Mon DD - Mon DD, YYYY" or "Month DD - Month DD, YYYY"
                date_match = re.search(
                    r"(\w{3,9}\s+\d{1,2})\s*[-–—]\s*(\w{3,9}\s+\d{1,2},?\s*\d{4})",
                    text,
                )
                if date_match:
                    date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                    start, end = self.parse_date_range(date_str)
                    break

            # Description from sibling text
            description = None
            for sibling in link.next_siblings:
                text = getattr(sibling, "get_text", lambda *a, **k: str(sibling))
                t = text(strip=True) if callable(text) else str(sibling).strip()
                if t and len(t) > 20 and t != title:
                    description = t[:300]
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
