"""Base scraper class for gallery exhibition pages."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None


DATA_DIR = Path(__file__).parent.parent / "data"


class BaseScraper:
    """Base class for all gallery scrapers."""

    school_id: str = ""
    exhibitions_url: str = ""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Some museum sites (e.g. Bennington) respond slowly and intermittently
    # blow past a single 30s attempt. Retry transient failures before giving up.
    FETCH_TIMEOUT = 45
    FETCH_RETRIES = 3

    def fetch(self, url: str | None = None) -> BeautifulSoup:
        """Fetch a page and return parsed BeautifulSoup.

        Uses curl_cffi with Chrome TLS impersonation when available;
        several museums (e.g. MFA Boston) sit behind Cloudflare, which
        403s plain requests based on TLS fingerprint alone.

        Retries transient failures (timeouts, connection resets) with a
        short backoff so a single slow response doesn't zero out a scraper.
        """
        url = url or self.exhibitions_url
        last_err: Exception | None = None
        for attempt in range(self.FETCH_RETRIES):
            try:
                if curl_requests is not None:
                    resp = curl_requests.get(url, impersonate="chrome", timeout=self.FETCH_TIMEOUT)
                else:
                    resp = requests.get(url, headers=self.HEADERS, timeout=self.FETCH_TIMEOUT)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "lxml")
            except Exception as e:  # noqa: BLE001 - retry any transient fetch error
                last_err = e
                if attempt < self.FETCH_RETRIES - 1:
                    time.sleep(2 * (attempt + 1))
        raise last_err

    def make_id(self, title: str) -> str:
        """Generate a stable ID from school_id + title."""
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return f"{self.school_id}-{slug}"

    def parse_date_range(self, text: str) -> tuple[str | None, str | None]:
        """Parse common date range formats into (start, end) ISO date strings.

        Handles:
          - "March 1 - May 15, 2026"
          - "March 1, 2026 - May 15, 2026"
          - "March 1 – May 15, 2026"  (en-dash)
          - "January 20—April 19, 2026" (em-dash)
          - "Through May 15, 2026"
          - "Opens March 1, 2026"
          - "Ongoing"
        """
        if not text:
            return None, None

        text = text.strip()
        # Normalize dashes
        text = text.replace("–", "-").replace("—", "-").replace("\u2013", "-").replace("\u2014", "-")

        # "Ongoing" or similar
        if re.match(r"(?i)^ongoing", text):
            return None, None

        # "Through <date>" / "To <date>"
        m = re.match(r"(?i)^(?:through|to)\s+(.+)", text)
        if m:
            end = self._parse_single_date(m.group(1))
            return None, end

        # Try splitting on dash
        parts = re.split(r"\s*-\s*", text, maxsplit=1)
        if len(parts) == 2:
            start_str, end_str = parts
            # If the start doesn't have a year, borrow from end
            end_date = self._parse_single_date(end_str)
            if end_date:
                year = end_date[:4]
                start_date = self._parse_single_date(start_str, default_year=year)
            else:
                start_date = self._parse_single_date(start_str)
            return start_date, end_date

        # Single date
        d = self._parse_single_date(text)
        return d, None

    def _parse_single_date(self, text: str, default_year: str | None = None) -> str | None:
        """Parse a single date string like 'March 1, 2026' or 'March 1'."""
        text = text.strip().rstrip(".")

        # Try "Month DD, YYYY"
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                dt = datetime.strptime(text, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Try "Month DD" (no year)
        for fmt in ("%B %d", "%b %d"):
            try:
                dt = datetime.strptime(text, fmt)
                year = default_year or str(datetime.now().year)
                return f"{year}-{dt.strftime('%m-%d')}"
            except ValueError:
                continue

        return None

    # Titles that are clearly not exhibitions
    SKIP_TITLES = {
        "visit", "learn more", "read more", "view exhibition", "view all",
        "exhibitions", "museum", "about", "contact", "hours", "directions",
        "support", "donate", "news", "event", "exhibition", "- any -",
        "view past exhibitions", "past exhibitions", "upcoming exhibitions",
        "current exhibitions", "press", "publications", "join & support",
        "marketing & communications", "sign out a space in porteous",
        "institute of contemporary art", "virtual exhibitions",
        "learn & explore", "upcoming events", "past events",
        "museum visit request form", "using the database", "introduction",
        "student involvement", "interns' blog", "museum podcast",
        "senior thesis exhibitions", "collection highlights",
        "common questions", "join our mailing list",
        "accessibility commitment for bennington museum",
    }

    @staticmethod
    def get_img_url(img, base_url: str = "") -> str | None:
        """Extract the real image URL from an <img> tag, handling lazy loading.

        Checks common lazy-load attributes in priority order:
        data-src, data-lazy-src, data-opt-src, srcset, then src.
        Skips data: URIs. Resolves relative URLs against base_url.
        """
        if not img:
            return None

        candidates = [
            img.get("data-src"),
            img.get("data-lazy-src"),
            img.get("data-opt-src"),
        ]

        # srcset: take the first URL
        srcset = img.get("data-lazy-srcset") or img.get("data-srcset") or img.get("srcset")
        if srcset:
            first = srcset.split(",")[0].strip().split(" ")[0]
            candidates.append(first)

        candidates.append(img.get("src"))

        for url in candidates:
            if not url:
                continue
            url = url.strip()
            if url.startswith("data:"):
                continue
            # Resolve relative URLs
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/") and base_url:
                # Root-relative
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                url = f"{parsed.scheme}://{parsed.netloc}{url}"
            elif not url.startswith("http") and base_url:
                # Relative path
                url = base_url.rstrip("/") + "/" + url
            return url

        return None

    def is_valid_exhibition(self, ex: dict) -> bool:
        """Filter out navigation links and other non-exhibition entries."""
        title = ex.get("title", "").strip()
        if not title or len(title) < 3:
            return False
        if title.lower() in self.SKIP_TITLES:
            return False
        # Skip data URIs as image URLs (lazy-load placeholders)
        if (ex.get("image_url") or "").startswith("data:"):
            ex["image_url"] = None
        return True

    def scrape(self) -> list[dict]:
        """Override in subclasses. Returns list of exhibition dicts."""
        raise NotImplementedError

    def run(self) -> list[dict]:
        """Run the scraper with error handling."""
        try:
            exhibitions = self.scrape()
            exhibitions = [ex for ex in exhibitions if self.is_valid_exhibition(ex)]
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            for ex in exhibitions:
                ex.setdefault("school_id", self.school_id)
                ex.setdefault("scraped_at", now)
                if "id" not in ex:
                    ex["id"] = self.make_id(ex.get("title", "unknown"))
            print(f"  [{self.school_id}] scraped {len(exhibitions)} exhibitions")
            return exhibitions
        except Exception as e:
            print(f"  [{self.school_id}] ERROR: {e}")
            return []
