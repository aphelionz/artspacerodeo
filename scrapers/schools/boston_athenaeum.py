"""Scraper for Boston Athenaeum."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class BostonAthenaeumScraper(BaseScraper):
    school_id = "boston-athenaeum"
    exhibitions_url = "https://www.bostonathenaeum.org/exhibitions/"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_titles = set()

        # Athenaeum has a main exhibition in h2 ("Imagined Nation") and
        # "Also On View" items in h3 with links to /whats-on/exhibitions/slug.
        # Skip "Upcoming" and "Past Exhibitions" sections.

        in_past = False

        # Process h2 (main exhibition) and h3 (secondary exhibitions)
        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(strip=True)

            if not text or len(text) < 3:
                continue

            text_lower = text.lower()

            # Track sections to skip
            if "past exhibition" in text_lower:
                in_past = True
                continue
            if text_lower in ("also on view", "upcoming", "exhibition related events"):
                continue
            if in_past:
                continue

            # Get link — h3s have links, h2 may not
            link = heading.find("a", href=True)
            if link:
                url = link.get("href", "")
                if not url.startswith("http"):
                    url = f"https://www.bostonathenaeum.org{url}"
                # Skip past exhibitions links
                if "past-exhibi" in url:
                    continue
            else:
                # For h2 without link, try parent
                parent = heading.find_parent(["div", "article", "section"])
                parent_link = parent.find("a", href=lambda h: h and "/exhibitions/" in h) if parent else None
                if parent_link:
                    url = parent_link.get("href", "")
                    if not url.startswith("http"):
                        url = f"https://www.bostonathenaeum.org{url}"
                else:
                    url = self.exhibitions_url

            if text in seen_titles:
                continue
            seen_titles.add(text)

            # Dates: look in parent container
            start_date, end_date = None, None
            parent = heading.find_parent(["div", "article", "section"])
            if parent:
                parent_text = parent.get_text(" ", strip=True)
                date_match = re.search(
                    r"(Through|through|On view.*?through|January|February|March|April|May|June|July|August|September|October|November|December)\s",
                    parent_text,
                )
                if date_match:
                    date_portion = parent_text[date_match.start():]
                    # Clean up
                    date_portion = re.sub(r"(?i)^on view\s*(now\s*)?", "", date_portion)
                    date_portion = re.split(r"[,.](?=\s*[A-Z])", date_portion)[0]
                    start_date, end_date = self.parse_date_range(date_portion.strip())

            # Image: walk up ancestors for img (uses Optimole: data-opt-src)
            image_url = None
            el = heading
            for _ in range(4):
                el = el.parent
                if not el:
                    break
                img = el.find("img")
                if img:
                    image_url = self.get_img_url(img, "https://www.bostonathenaeum.org")
                    if image_url:
                        break

            exhibitions.append({
                "title": text,
                "start_date": start_date,
                "end_date": end_date,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
