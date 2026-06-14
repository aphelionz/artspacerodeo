"""Scraper for Isabella Stewart Gardner Museum."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class GardnerScraper(BaseScraper):
    school_id = "gardner"
    exhibitions_url = "https://www.gardnermuseum.org/exhibitions"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_urls = set()

        # Gardner has a simple exhibitions page with h3 titles linking to
        # /calendar/exhibition/slug. Limited metadata on the listing page.
        links = soup.find_all("a", href=lambda h: h and "/calendar/exhibition/" in h)

        for link in links:
            href = link.get("href", "")
            if href in seen_urls:
                continue
            seen_urls.add(href)

            url = href
            if not url.startswith("http"):
                url = f"https://www.gardnermuseum.org{url}"

            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Image: walk up through ancestors looking for img
            image_url = None
            el = link
            for _ in range(4):
                el = el.parent
                if not el:
                    break
                img = el.find("img")
                if img:
                    image_url = self.get_img_url(img, "https://www.gardnermuseum.org")
                    if image_url:
                        break

            # Dates: look in parent text
            parent = link.find_parent(["div", "article", "section"])
            start_date, end_date = None, None
            if parent:
                parent_text = parent.get_text(" ", strip=True)
                date_match = re.search(
                    r"(Through\s|January|February|March|April|May|June|July|August|September|October|November|December)",
                    parent_text,
                )
                if date_match:
                    date_portion = parent_text[date_match.start():]
                    # Take only the first line/sentence
                    date_portion = re.split(r"[.\n]", date_portion)[0]
                    start_date, end_date = self.parse_date_range(date_portion)

            exhibitions.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
