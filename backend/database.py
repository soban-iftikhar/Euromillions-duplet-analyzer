import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data.db"))


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pairs (
                num1 INTEGER NOT NULL,
                num2 INTEGER NOT NULL,
                frequency INTEGER NOT NULL,
                PRIMARY KEY (num1, num2)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bands (
                frequency INTEGER PRIMARY KEY,
                count INTEGER NOT NULL,
                percentage REAL NOT NULL,
                pairs_listed INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def save_scrape(pairs, bands, scraped_at: str, note: Optional[str], source_url: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM pairs")
        conn.execute("DELETE FROM bands")
        conn.executemany(
            "INSERT INTO pairs (num1, num2, frequency) VALUES (?, ?, ?)",
            [(p.num1, p.num2, p.frequency) for p in pairs],
        )
        conn.executemany(
            "INSERT INTO bands (frequency, count, percentage, pairs_listed) VALUES (?, ?, ?, ?)",
            [(b.frequency, b.count, b.percentage, int(b.pairs_listed)) for b in bands],
        )
        _set_meta(conn, "last_scraped", scraped_at)
        _set_meta(conn, "pair_count", str(len(pairs)))
        _set_meta(conn, "note", note or "")
        _set_meta(conn, "source_url", source_url)
        conn.commit()


def _set_meta(conn, key: str, value: str):
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM meta").fetchall()
        return {k: v for k, v in rows}


def get_all_pairs() -> dict[tuple[int, int], int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT num1, num2, frequency FROM pairs").fetchall()
        return {(n1, n2): freq for n1, n2, freq in rows}


def get_bands() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT frequency, count, percentage, pairs_listed FROM bands ORDER BY frequency DESC"
        ).fetchall()
        return [
            {
                "frequency": f,
                "count": c,
                "percentage": pct,
                "pairs_listed": bool(pl),
            }
            for f, c, pct, pl in rows
        ]
