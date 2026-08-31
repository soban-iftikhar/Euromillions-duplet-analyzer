"""
Run this from your own machine (not from Render/Vercel/any cloud host) to
scrape the live site and push the result into your deployed backend.

Why this exists: lottery.merseyworld.com is behind Cloudflare, which blocks
requests coming from most cloud/hosting-provider IP ranges (Render, AWS,
Vercel, Railway, Fly.io, etc.) regardless of headers/User-Agent. A normal
home/office internet connection is not blocked, so scraping works fine from
here — it just needs to be pushed to the deployed backend afterwards.

Usage:
    export BACKEND_URL="https://your-app.onrender.com"
    export IMPORT_SECRET="the-same-secret-you-set-on-render"
    python scripts/local_scrape_and_push.py

Run this whenever you want the deployed app's data refreshed (e.g. after
each EuroMillions draw).
"""

import os
import sys
from dataclasses import asdict

# allow running from repo root or from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import requests
from scraper import scrape_pairs  # noqa: E402

BACKEND_URL = os.environ.get("BACKEND_URL")
IMPORT_SECRET = os.environ.get("IMPORT_SECRET")


def main():
    if not BACKEND_URL:
        print("Set BACKEND_URL env var, e.g. https://your-app.onrender.com")
        sys.exit(1)
    if not IMPORT_SECRET:
        print("Set IMPORT_SECRET env var (must match the one set on the backend).")
        sys.exit(1)

    print("Scraping live site from this machine...")
    result = scrape_pairs()
    print(f"Scraped {len(result.pairs)} pairs across {len(result.bands)} frequency bands.")

    payload = {
        "secret": IMPORT_SECRET,
        "pairs": [asdict(p) for p in result.pairs],
        "bands": [asdict(b) for b in result.bands],
        "scraped_at": result.scraped_at,
        "note": result.note,
        "source_url": result.source_url,
    }

    url = BACKEND_URL.rstrip("/") + "/api/import"
    print(f"Pushing data to {url} ...")
    resp = requests.post(url, json=payload, timeout=30)

    if resp.status_code != 200:
        print(f"Failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    print("Done:", resp.json())


if __name__ == "__main__":
    main()
