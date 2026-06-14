"""Scraper for Hood Museum of Art at Dartmouth College."""

import re

from scrapers.base import BaseScraper


class HoodScraper(BaseScraper):
    school_id = "hood"
    exhibitions_url = "https://hoodmuseum.dartmouth.edu/explore/on-view"

    def scrape(self):
        soup = self.fetch()
        exhibitions = []

        # Hood Museum uses Drupal; exhibition cards link to /explore/exhibitions/slug
        for link in soup.select('a[href*="/exhibitions/"]'):
            href = link.get("href", "")
            if href in ("/explore/exhibitions", "/explore/exhibitions/"):
                continue

            # Get title from heading inside the link or link text
            title_el = link.select_one("h2, h3, h4")
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)

            if not title or len(title) < 3:
                continue
            if title.lower() in ("learn more", "learn more >", "view all"):
                continue

            url = href if href.startswith("http") else f"https://hoodmuseum.dartmouth.edu{href}"

            img = link.select_one("img")
            image_url = self.get_img_url(img, "https://hoodmuseum.dartmouth.edu")
            # Also check parent article for images
            if not image_url:
                article = link.find_parent("article")
                if article:
                    img = article.select_one("img")
                    image_url = self.get_img_url(img, "https://hoodmuseum.dartmouth.edu")

            # Find date in surrounding container
            container = link.find_parent(["div", "article", "section"])
            start, end = None, None
            description = None

            if container:
                text = container.get_text(" ", strip=True)
                # Hood uses "Month DD – Month DD, YYYY"
                date_match = re.search(
                    r"(\w+ \d{1,2})\s*[-–—]\s*(\w+ \d{1,2},?\s*\d{4})",
                    text,
                )
                if date_match:
                    date_str = f"{date_match.group(1)} - {date_match.group(2)}"
                    start, end = self.parse_date_range(date_str)

                # Try to get description from <p> tags
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

        # Deduplicate by URL
        seen = set()
        unique = []
        for ex in exhibitions:
            if ex["url"] not in seen:
                seen.add(ex["url"])
                unique.append(ex)

        return unique
