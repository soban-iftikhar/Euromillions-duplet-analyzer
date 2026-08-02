from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://lottery.merseyworld.com/Euro/Analysis/Pairs.html"

BLOCK_HEADER_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)%\s*(.*)$")
PAIR_TOKEN_RE = re.compile(r"^\d{1,2}$")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


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
    soup = BeautifulSoup(html, "html.parser")
    pre = soup.find("pre")
    if pre is None:
        raise ValueError("Could not find <pre> block on page — site structure may have changed.")

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
            continue
        if raw_line.strip().lower().startswith("tot"):
            flush()
            continue

        m = BLOCK_HEADER_RE.match(raw_line)
        if m:
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
            if current_freq is not None:
                current_tokens.extend(raw_line.split())

    flush()
    return pairs, bands


def scrape_pairs(timeout: int = 20) -> ScrapeResult:
    resp = requests.get(
        SOURCE_URL,
        timeout=timeout,
        headers=DEFAULT_HEADERS,
    )
    resp.raise_for_status()
    pre_text, note = _extract_pre_text(resp.text)
    pairs, bands = _parse_pre_text(pre_text)
    return ScrapeResult(
        pairs=pairs,
        bands=bands,
        note=note,
        scraped_at=datetime.now(timezone.utc).isoformat(),
        source_url=SOURCE_URL,
    )


def parse_pre_text_for_testing(pre_text: str) -> tuple[list[PairRecord], list[FrequencyBand]]:
    return _parse_pre_text(pre_text)