#!/usr/bin/env python3
"""Run all gallery scrapers and write exhibitions.json."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from collections import Counter
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

# A scraper whose selectors silently stop matching returns a small number
# rather than raising, so error handling never sees it. Flag a venue only
# when it falls by BOTH a large fraction and a meaningful absolute count:
# small venues legitimately swing (bates goes 5 -> 2 on its own), while a
# broken PEM goes 28 -> 2 and trips both. A tiny venue collapsing all the
# way to 0 slips under the absolute floor, but a scraper returning 0 is
# already obvious in the per-scraper counts above.
DROP_FRACTION = 0.40
DROP_ABSOLUTE = 4

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


def load_counts(path: Path) -> Counter:
    """Count exhibitions per school_id in an existing data file.

    Returns an empty Counter if the file is missing or unreadable, so a
    first run (or one recovering from a bad file) simply has no baseline.
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return Counter()
    return Counter(ex.get("school_id") for ex in data if ex.get("school_id"))


def report_drops(previous: Counter, current: Counter) -> list[str]:
    """Return warnings for venues that fell sharply since the last run."""
    warnings = []
    for school_id, was in sorted(previous.items()):
        now = current.get(school_id, 0)
        lost = was - now
        if lost >= DROP_ABSOLUTE and lost >= was * DROP_FRACTION:
            warnings.append(f"{school_id}: {was} -> {now} ({lost} fewer)")
    return warnings


def write_json(path: Path, data: list[dict]) -> None:
    """Write JSON via a temp file and atomic rename.

    Writing in place would truncate the existing file before the new
    contents land, so a crash mid-write would destroy the only good copy.
    """
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


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

    output = DATA_DIR / "exhibitions.json"
    archive = DATA_DIR / "exhibitions_archive.json"

    # Read the baseline before overwriting it
    previous_counts = load_counts(output)
    warnings = report_drops(previous_counts, Counter(ex["school_id"] for ex in current))

    write_json(output, current)
    write_json(archive, past)

    print(f"\nDone. {len(current)} current exhibitions, {len(past)} past.")
    print(f"  Current → {output}")
    print(f"  Archive → {archive}")

    if warnings:
        print(f"\nWARNING: {len(warnings)} venue(s) dropped sharply since the last run:")
        for line in warnings:
            print(f"  {line}")
        print("  Check whether the site changed and the selectors went stale.")


if __name__ == "__main__":
    main()
