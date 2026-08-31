import os
from itertools import combinations
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database
from scraper import scrape_pairs, PairRecord, FrequencyBand

app = FastAPI(title="EuroMillions Duplet Analyzer")

IMPORT_SECRET = os.environ.get("IMPORT_SECRET")

# Allow the frontend (any origin, since this is a tiny 1-2 user internal tool).
# Tighten this to your actual Vercel URL if you want it locked down.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()


class AnalyzeRequest(BaseModel):
    numbers: list[int] = Field(..., min_length=2, description="Numbers to combine into duplets")
    use_fresh: bool = Field(False, description="If true, re-scrape the source site before analyzing")


class ImportPair(BaseModel):
    num1: int
    num2: int
    frequency: int


class ImportBand(BaseModel):
    frequency: int
    count: int
    percentage: float
    pairs_listed: bool


class ImportRequest(BaseModel):
    secret: str
    pairs: list[ImportPair]
    bands: list[ImportBand]
    scraped_at: str
    note: Optional[str] = None
    source_url: Optional[str] = None


@app.get("/api/status")
def status():
    meta = database.get_meta()
    return {
        "last_scraped": meta.get("last_scraped"),
        "pair_count": int(meta.get("pair_count", 0)),
        "source_url": meta.get("source_url"),
        "note": meta.get("note"),
        "has_data": bool(meta.get("last_scraped")),
    }


@app.post("/api/scrape")
def scrape():
    try:
        result = scrape_pairs()
    except Exception as exc:  # noqa: BLE001
        detail = f"Failed to scrape source site: {exc}"
        if "403" in str(exc):
            detail += (
                " — this is very likely the source site's Cloudflare protection blocking "
                "requests from cloud/hosting IP ranges (Render, AWS, etc.), not a code bug. "
                "Use the local scrape-and-push script instead (see README) to update this "
                "backend's data from a normal residential IP."
            )
        raise HTTPException(status_code=502, detail=detail)

    database.save_scrape(
        pairs=result.pairs,
        bands=result.bands,
        scraped_at=result.scraped_at,
        note=result.note,
        source_url=result.source_url,
    )
    return {
        "scraped_at": result.scraped_at,
        "pair_count": len(result.pairs),
        "band_count": len(result.bands),
        "note": result.note,
    }


@app.post("/api/import")
def import_data(req: ImportRequest):
    """
    Accepts pre-scraped data (produced locally, e.g. via scripts/local_scrape_and_push.py)
    and stores it. Exists because the live site blocks requests from most cloud hosting
    IP ranges, so scraping directly from the deployed backend often isn't possible.
    """
    if not IMPORT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="IMPORT_SECRET is not configured on the server. Set it as an env var first.",
        )
    if req.secret != IMPORT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret.")

    pairs = [PairRecord(p.num1, p.num2, p.frequency) for p in req.pairs]
    bands = [
        FrequencyBand(b.frequency, b.count, b.percentage, b.pairs_listed) for b in req.bands
    ]

    database.save_scrape(
        pairs=pairs,
        bands=bands,
        scraped_at=req.scraped_at,
        note=req.note,
        source_url=req.source_url,
    )
    return {
        "scraped_at": req.scraped_at,
        "pair_count": len(pairs),
        "band_count": len(bands),
    }


@app.get("/api/bands")
def bands():
    return database.get_bands()


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if req.use_fresh:
        scrape()

    meta = database.get_meta()
    if not meta.get("last_scraped"):
        raise HTTPException(
            status_code=400,
            detail="No historical data available yet. Run a scrape first (use the Refresh button).",
        )

    numbers = sorted(set(req.numbers))
    if len(numbers) < 2:
        raise HTTPException(status_code=400, detail="Enter at least 2 distinct numbers.")

    out_of_range = [n for n in numbers if n < 1 or n > 50]

    generated = list(combinations(numbers, 2))
    pair_lookup = database.get_all_pairs()

    matched = []
    unmatched = []
    for a, b in generated:
        freq = pair_lookup.get((a, b))
        if freq is not None:
            matched.append({"pair": [a, b], "frequency": freq})
        else:
            unmatched.append({"pair": [a, b]})

    matched.sort(key=lambda x: x["frequency"], reverse=True)

    return {
        "input_numbers": numbers,
        "out_of_range_numbers": out_of_range,
        "generated_pairs": [{"pair": [a, b]} for a, b in generated],
        "matched_pairs": matched,
        "unmatched_pairs": unmatched,
        "data_source": {
            "last_scraped": meta.get("last_scraped"),
            "pair_count": int(meta.get("pair_count", 0)),
        },
    }
