"""
Scraper for https://lottery.merseyworld.com/Euro/Analysis/Pairs.html

The page structure (inside a <pre> tag) looks like:

    Freq      #   %age                           Pairs

     29       1   0.08%    04 23

     28       7   0.57%    01 48    10 45    15 28    19 37    23 24    23 37
                           39 44
     ...
     15     124  10.12%

    Tot  1,225 100.00%

Each "block" starts with a line matching: <freq> <count> <pct>%  [pairs...]
Pairs for that block may continue on following indented lines until the
next block-header line or a blank line followed by a new block.

IMPORTANT LIMITATION (confirmed from the live page as of Aug 2026):
The site only lists the *individual* pair numbers for frequency bands that
have appeared more than a threshold (currently >15 times, i.e. freq >= 16).
For freq <= 15 it only gives the aggregate count/percentage for that band,
not which specific pairs fall into it. So our "known pairs" table only ever
contains the subset of the 1225 possible pairs that appear in bands with an
explicit list. Everything else is "unknown" (not necessarily zero — we just
don't have the specific pair identity for it).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://lottery.merseyworld.com/Euro/Analysis/Pairs.html"

BLOCK_HEADER_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)%\s*(.*)$")
PAIR_TOKEN_RE = re.compile(r"^\d{1,2}$")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# The source site is behind Cloudflare, which blocks requests from most cloud/
# hosting-provider IP ranges outright (Render, AWS, Vercel, etc.), regardless
# of headers. If SCRAPER_PROXY_API_KEY is set, requests are routed through
# ScraperAPI (https://www.scraperapi.com — free tier is enough for this site,
# since we only fetch one small static page a few times a day), which uses
# IPs that aren't blocked. Without the key, we fall back to a direct request
# (works fine locally, will likely 403 from most cloud hosts).
SCRAPER_PROXY_API_KEY = os.environ.get("SCRAPER_PROXY_API_KEY")


def _fetch_html(url: str, timeout: int) -> str:
    if SCRAPER_PROXY_API_KEY:
        proxy_url = (
            f"http://api.scraperapi.com/?api_key={SCRAPER_PROXY_API_KEY}&url={quote(url, safe='')}"
        )
        resp = requests.get(proxy_url, timeout=timeout)
    else:
        resp = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
    resp.raise_for_status()
    return resp.text


@dataclass
class PairRecord:
    num1: int
    num2: int
    frequency: int


@dataclass
class FrequencyBand:
    frequency: int
    count: int
    percentage: float
    pairs_listed: bool


@dataclass
class ScrapeResult:
    pairs: list[PairRecord]
    bands: list[FrequencyBand]
    note: Optional[str]
    scraped_at: str
    source_url: str


def _extract_pre_text(html: str) -> tuple[str, Optional[str]]:
    """Return (pre_text, intro_note) from the page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    pre = soup.find("pre")
    if pre is None:
        raise ValueError("Could not find <pre> block on page — site structure may have changed.")

    # Try to grab the descriptive sentence right above the <pre> (explains the
    # frequency cutoff, e.g. "...appeared more than ... fifteen times...").
    note = None
    p = pre.find_previous("p")
    if p and p.get_text(strip=True):
        note = p.get_text(strip=True)

    return pre.get_text(), note


def _parse_pre_text(pre_text: str) -> tuple[list[PairRecord], list[FrequencyBand]]:
    pairs: list[PairRecord] = []
    bands: list[FrequencyBand] = []

    lines = pre_text.split("\n")
    current_freq: Optional[int] = None
    current_tokens: list[str] = []

    def flush():
        nonlocal current_freq, current_tokens
        if current_freq is None:
            return
        # group tokens two at a time into pairs
        toks = current_tokens
        for i in range(0, len(toks) - 1, 2):
            a, b = toks[i], toks[i + 1]
            if PAIR_TOKEN_RE.match(a) and PAIR_TOKEN_RE.match(b):
                n1, n2 = int(a), int(b)
                if n1 > n2:
                    n1, n2 = n2, n1
                pairs.append(PairRecord(n1, n2, current_freq))
        current_freq = None
        current_tokens = []

    for raw_line in lines:
        if not raw_line.strip():
            continue
        if raw_line.strip().lower().startswith("freq") and "pairs" in raw_line.lower():
            continue  # header row
        if raw_line.strip().lower().startswith("tot"):
            flush()
            continue

        m = BLOCK_HEADER_RE.match(raw_line)
        if m:
            # a new block starts -> flush the previous one first
            flush()
            freq = int(m.group(1))
            count = int(m.group(2))
            pct = float(m.group(3))
            rest = m.group(4).strip()
            current_freq = freq
            current_tokens = rest.split() if rest else []
            bands.append(
                FrequencyBand(
                    frequency=freq,
                    count=count,
                    percentage=pct,
                    pairs_listed=bool(rest),
                )
            )
        else:
            # continuation line of pairs for the current block
            if current_freq is not None:
                current_tokens.extend(raw_line.split())

    flush()
    return pairs, bands


def scrape_pairs(timeout: int = 30) -> ScrapeResult:
    html = _fetch_html(SOURCE_URL, timeout=timeout)
    pre_text, note = _extract_pre_text(html)
    pairs, bands = _parse_pre_text(pre_text)
    return ScrapeResult(
        pairs=pairs,
        bands=bands,
        note=note,
        scraped_at=datetime.now(timezone.utc).isoformat(),
        source_url=SOURCE_URL,
    )


def parse_pre_text_for_testing(pre_text: str) -> tuple[list[PairRecord], list[FrequencyBand]]:
    """Exposed for local testing without hitting the network."""
    return _parse_pre_text(pre_text)
