"""Scraper for MECA&D (Maine College of Art & Design)."""

from scrapers.base import BaseScraper


# Title keywords that mark an entry as an exhibition.
EXHIBITION_KEYWORDS = (
    "exhibition",
    "exhibit",
    "thesis",
    "triennial",
    "biennial",
    "at 49 oak",
)

# Title keywords that disqualify an entry (info sessions, talks, etc.).
NON_EXHIBITION_KEYWORDS = (
    "info session",
    "open house",
    "webinar",
    "panel",
    "screening",
    "workshop",
    "fashion show",
    "film festival",
    "documentary showcase",
    "holiday sale",
    "art sale",
    "market",
    "virtual student panel",
    "student panel",
    "portfolio prep",
    "application prep",
    "alumni panel",
    "visiting artist",
    "reception",
    "opening reception",
)


class MECAScraper(BaseScraper):
    school_id = "meca"
    exhibitions_url = "https://meca.edu/events/"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []
        seen = set()

        for link in soup.select('a[href^="/event/"]'):
            href = link.get("href", "")
            if href in seen:
                continue
            seen.add(href)

            title_el = link.find(["h2", "h3", "h4", "h5"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            lower = title.lower()
            if any(kw in lower for kw in NON_EXHIBITION_KEYWORDS):
                continue
            if not any(kw in lower for kw in EXHIBITION_KEYWORDS):
                continue

            date_el = link.find("p")
            date_text = date_el.get_text(strip=True) if date_el else ""
            start, end = self.parse_date_range(date_text) if date_text else (None, None)
            # MECA mixes single-day events (talks, openings) with exhibitions in
            # the same /events/ feed. Real exhibitions always have a date range.
            if not end:
                continue

            img = link.select_one("img[data-src], img[src]")
            image_url = self.get_img_url(img, "https://meca.edu") if img else None

            exhibitions.append({
                "title": title,
                "start_date": start,
                "end_date": end,
                "url": f"https://meca.edu{href}",
                "image_url": image_url,
                "description": None,
            })

        return exhibitions
