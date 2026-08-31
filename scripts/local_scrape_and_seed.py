"""
Run this locally, then commit and push the file it writes.

Why this exists: Render's free-tier disk is ephemeral — it resets on every
restart (including the idle spin-down/wake-up cycle), so anything written
to the database at runtime (via /api/scrape or /api/import) disappears the
next time the service restarts. A file committed to the git repo, on the
other hand, is part of every deploy and gets reloaded automatically on
every startup (see main.py's _seed_from_file_if_needed). That's what
actually makes the data stick.

Usage:
    python scripts/local_scrape_and_seed.py
    git add backend/seed_data.json
    git commit -m "Update lottery pair data"
    git push
    (Render auto-deploys on push, and the new data loads automatically.)

Run this whenever you want the live app's data refreshed — e.g. after each
EuroMillions draw (Tuesday/Friday).
"""

import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from scraper import scrape_pairs  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "seed_data.json")


def main():
    print("Scraping live site from this machine...")
    result = scrape_pairs()
    print(f"Scraped {len(result.pairs)} pairs across {len(result.bands)} frequency bands.")

    seed = {
        "pairs": [asdict(p) for p in result.pairs],
        "bands": [asdict(b) for b in result.bands],
        "scraped_at": result.scraped_at,
        "note": result.note,
        "source_url": result.source_url,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(seed, f, indent=2)

    print(f"Wrote {OUT_PATH}")
    print()
    print("Next steps:")
    print("  git add backend/seed_data.json")
    print('  git commit -m "Update lottery pair data"')
    print("  git push")


if __name__ == "__main__":
    main()
