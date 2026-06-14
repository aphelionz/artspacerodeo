"""Scraper for Colby College Museum of Art."""

from __future__ import annotations

from curl_cffi import requests as cf_requests

from scrapers.base import BaseScraper

API_URL = "https://museum-backend.colby.edu/wp-json/custom/v1/exhibitions?chronology=current"
FRONTEND_BASE = "https://museum.colby.edu"


class ColbyScraper(BaseScraper):
    school_id = "colby"
    # colby.edu and museum.colby.edu are behind Cloudflare (403 for all scrapers).
    # museum-backend.colby.edu exposes a public WP REST API that bypasses this.
    exhibitions_url = API_URL

    def scrape(self):
        try:
            r = cf_requests.get(API_URL, impersonate="chrome124", timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  [{self.school_id}] API fetch failed: {e}")
            return []

        exhibitions = []
        for item in data:
            title = item.get("title", {}).get("rendered", "").strip()
            if not title:
                continue

            acf = item.get("acf", {})
            start = self._parse_acf_date(acf.get("date"))
            end = self._parse_acf_date(acf.get("end_date"))

            slug = item.get("slug", "")
            url = f"{FRONTEND_BASE}/exhibitions/{slug}" if slug else FRONTEND_BASE

            image_url = None
            media_list = item.get("_embedded", {}).get("wp:featuredmedia", [])
            if media_list:
                guid = media_list[0].get("guid", {}).get("rendered")
                if guid:
                    image_url = guid

            description = item.get("post_excerpt") or item.get("content") or None
            if description:
                from bs4 import BeautifulSoup
                description = BeautifulSoup(description, "lxml").get_text(strip=True)[:300]

            exhibitions.append({
                "title": title,
                "start_date": start,
                "end_date": end,
                "url": url,
                "image_url": image_url,
                "description": description or None,
            })

        return exhibitions

    @staticmethod
    def _parse_acf_date(val: str | None) -> str | None:
        """Parse ACF date format YYYYMMDD → YYYY-MM-DD."""
        if not val or len(val) != 8:
            return None
        return f"{val[:4]}-{val[4:6]}-{val[6:8]}"
