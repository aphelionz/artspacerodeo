"""Scraper for Brattleboro Museum & Art Center."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BrattleboroScraper(BaseScraper):
    school_id = "brattleboro"
    exhibitions_url = "https://www.brattleboromuseum.org/exhibits/current-exhibits/"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []

        # Brattleboro lists exhibitions with h2 titles containing links.
        # Siblings contain description and date text.
        h2s = soup.find_all("h2")

        for h2 in h2s:
            link = h2.find("a", href=True)
            if not link:
                continue

            title = h2.get_text(strip=True)
            url = link.get("href", "")
            if not url.startswith("http"):
                url = f"https://www.brattleboromuseum.org{url}"

            # Image: look in parent container
            parent = h2.find_parent(["div", "article", "section"])
            image_url = None
            if parent:
                img = parent.find("img")
                image_url = self.get_img_url(img, "https://www.brattleboromuseum.org")

            # Date and description from next siblings
            start_date, end_date = None, None
            description = None
            sibs = h2.find_next_siblings(["p", "span", "div"], limit=3)
            for sib in sibs:
                sib_text = sib.get_text(strip=True)
                if not sib_text:
                    continue
                # Check if this looks like a date
                date_match = re.search(
                    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                    r"\s+\d{1,2}",
                    sib_text,
                )
                if date_match and not start_date and not end_date:
                    start_date, end_date = self.parse_date_range(sib_text)
                elif not description and len(sib_text) > 20:
                    description = sib_text[:300]

            exhibitions.append({
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": description,
            })

        return exhibitions
