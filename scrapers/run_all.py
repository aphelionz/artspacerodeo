#!/usr/bin/env python3
"""Run all gallery scrapers and write exhibitions.json."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

# College galleries
from scrapers.schools.bowdoin import BowdoinScraper
from scrapers.schools.bates import BatesScraper
from scrapers.schools.colby import ColbyScraper
from scrapers.schools.meca import MECAScraper
from scrapers.schools.massart import MassArtScraper
from scrapers.schools.brandeis import BrandeisScraper
from scrapers.schools.middlebury import MiddleburyScraper
from scrapers.schools.hood import HoodScraper

# Museums
from scrapers.schools.pma import PMAScraper
from scrapers.schools.farnsworth import FarnsworthScraper
from scrapers.schools.mfa_boston import MFABostonScraper
from scrapers.schools.ica_boston import ICABostonScraper
from scrapers.schools.gardner import GardnerScraper
from scrapers.schools.pem import PEMScraper
from scrapers.schools.boston_athenaeum import BostonAthenaeumScraper
from scrapers.schools.brattleboro import BrattleboroScraper
from scrapers.schools.bennington import BenningtonScraper
from scrapers.schools.currier import CurrierScraper

DATA_DIR = Path(__file__).parent.parent / "data"

SCRAPERS = [
    # College galleries
    BowdoinScraper(),
    BatesScraper(),
    ColbyScraper(),
    MECAScraper(),
    MassArtScraper(),
    BrandeisScraper(),
    MiddleburyScraper(),
    HoodScraper(),
    # Museums
    PMAScraper(),
    FarnsworthScraper(),
    MFABostonScraper(),
    ICABostonScraper(),
    GardnerScraper(),
    PEMScraper(),
    BostonAthenaeumScraper(),
    BrattleboroScraper(),
    BenningtonScraper(),
    CurrierScraper(),
]


def is_current_or_upcoming(exhibition: dict) -> bool:
    """Return True if exhibition is current or upcoming (not past)."""
    end_date = exhibition.get("end_date")
    if not end_date:
        # No end date — assume current
        return True
    try:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return end >= datetime.now().date()
    except ValueError:
        return True


def main():
    print("Scraping gallery exhibitions...\n")
    all_exhibitions = []

    for scraper in SCRAPERS:
        results = scraper.run()
        all_exhibitions.extend(results)
        # Be polite: small delay between institutions
        time.sleep(1)

    # Split into current and past
    current = [ex for ex in all_exhibitions if is_current_or_upcoming(ex)]
    past = [ex for ex in all_exhibitions if not is_current_or_upcoming(ex)]

    # Write current exhibitions (main data file for the site)
    output = DATA_DIR / "exhibitions.json"
    with open(output, "w") as f:
        json.dump(current, f, indent=2)

    # Write past exhibitions (archive)
    archive = DATA_DIR / "exhibitions_archive.json"
    with open(archive, "w") as f:
        json.dump(past, f, indent=2)

    print(f"\nDone. {len(current)} current exhibitions, {len(past)} past.")
    print(f"  Current → {output}")
    print(f"  Archive → {archive}")


if __name__ == "__main__":
    main()
