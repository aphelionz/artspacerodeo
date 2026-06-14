"""Scraper for Peabody Essex Museum."""

from __future__ import annotations

import re

from scrapers.base import BaseScraper


class PEMScraper(BaseScraper):
    school_id = "pem"
    exhibitions_url = "https://www.pem.org/exhibitions"

    def scrape(self) -> list[dict]:
        soup = self.fetch()
        exhibitions = []
        seen_urls = set()

        # PEM has exhibition links to /exhibitions/slug.
        # Some links are "Learn more" buttons deep in slider/card structures.
        # Best approach: collect all unique exhibition URLs, then for each,
        # try to find a title from the surrounding DOM or derive from slug.

        links = soup.find_all("a", href=lambda h: h and "/exhibitions/" in h)

        for link in links:
            href = link.get("href", "")
            url = href if href.startswith("http") else f"https://www.pem.org{href}"

            # Skip the main listings page and anchors
            if url.rstrip("/") in ("https://www.pem.org/exhibitions",):
                continue
            if "#" in url:
                continue

            # Normalize URL for dedup
            url_key = url.rstrip("/")
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)

            # Title: prefer link text if it's not "Learn more"
            title = link.get_text(strip=True)
            if not title or title.lower() in ("learn more", "see what's on view", ""):
                # Walk up to find a heading
                found = False
                el = link
                for _ in range(6):
                    el = el.parent
                    if not el:
                        break
                    heading = el.find(["h1", "h2", "h3"], recursive=False)
                    if heading:
                        title = heading.get_text(strip=True)
                        found = True
                        break
                if not found:
                    # Derive from URL slug
                    slug = url.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").title()

            if not title or len(title) < 3:
                continue

            # Image: walk up to find img
            image_url = None
            el = link
            for _ in range(5):
                el = el.parent
                if not el:
                    break
                img = el.find("img")
                if img:
                    src = img.get("data-src") or img.get("src", "")
                    if not src.startswith("data:"):
                        image_url = src
                        break

            exhibitions.append({
                "title": title,
                "start_date": None,
                "end_date": None,
                "url": url,
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
