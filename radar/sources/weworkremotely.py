"""WeWorkRemotely source — RSS feed for backend programming jobs."""

from __future__ import annotations

import hashlib
from datetime import datetime

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_RSS_URL = "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"


class WeWorkRemotelySource(Source):
    """Fetches backend remote jobs from WeWorkRemotely RSS feed."""

    name = "weworkremotely"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        import feedparser

        resp = await client.get(_RSS_URL, timeout=10.0)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        postings: list[JobPosting] = []
        for entry in feed.entries:
            url = entry.get("link") or entry.get("id") or ""
            if not url:
                continue
            uid = hashlib.md5(url.encode()).hexdigest()

            # Title format: "Company: Role Title"
            raw_title: str = entry.get("title") or ""
            if ": " in raw_title:
                company, title = raw_title.split(": ", 1)
            else:
                company, title = "Unknown", raw_title

            # Parse published date
            published = entry.get("published")
            posted_at: datetime | None = None
            if published:
                try:
                    import email.utils
                    parsed = email.utils.parsedate_to_datetime(published)
                    posted_at = parsed
                except Exception:
                    posted_at = None

            summary = entry.get("summary") or ""

            postings.append(
                JobPosting(
                    id=uid,
                    title=title.strip(),
                    company=company.strip(),
                    url=url,
                    location="Remote",
                    body=summary,
                    posted_at=posted_at,
                    source=self.name,
                )
            )
        return postings
