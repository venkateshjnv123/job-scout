"""SQLite-backed deduplication — skips already-seen job URLs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import structlog

from radar.models import JobPosting

log = structlog.get_logger()

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    url TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL
)
"""


class SeenStore:
    """Tracks which job URLs have already been included in a digest."""

    def __init__(self, db_path: str = "./seen.db") -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def filter_new(self, postings: list[JobPosting]) -> list[JobPosting]:
        """Return only postings not previously seen."""
        new: list[JobPosting] = []
        for p in postings:
            row = self._conn.execute(
                "SELECT 1 FROM seen_jobs WHERE url = ?", (p.url,)
            ).fetchone()
            if not row:
                new.append(p)
        log.info("dedup", total=len(postings), new=len(new), skipped=len(postings) - len(new))
        return new

    def mark_seen(self, postings: list[JobPosting]) -> None:
        """Record postings as seen."""
        from datetime import date
        today = date.today().isoformat()
        self._conn.executemany(
            "INSERT OR IGNORE INTO seen_jobs (url, first_seen) VALUES (?, ?)",
            [(p.url, today) for p in postings],
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SeenStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
