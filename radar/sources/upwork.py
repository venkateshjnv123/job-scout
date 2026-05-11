"""Upwork RSS source — public feed, no auth, freelance/gig track."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_RSS_URL = "https://www.upwork.com/ab/feed/jobs/rss"
_SEARCHES = [
    "java spring backend",
    "python backend developer",
    "ai trainer",
    "prompt engineer",
]
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


class UpworkSource(Source):
    name = "upwork"
    track = "gig"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        seen: set[str] = set()
        postings: list[JobPosting] = []
        for q in _SEARCHES:
            postings.extend(await self._fetch_query(client, q, seen))
        return postings

    async def _fetch_query(
        self, client: httpx.AsyncClient, q: str, seen: set[str]
    ) -> list[JobPosting]:
        resp = await client.get(
            _RSS_URL,
            params={"q": q, "sort": "recency"},
            headers=_HEADERS,
            timeout=15.0,
        )
        resp.raise_for_status()

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return []

        postings: list[JobPosting] = []
        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            if not link or link in seen:
                continue
            seen.add(link)

            uid = hashlib.md5(link.encode()).hexdigest()
            title = (item.findtext("title") or "").strip()
            desc = (item.findtext("description") or "").strip()

            posted_at: datetime | None = None
            pub_date = item.findtext("pubDate")
            if pub_date:
                try:
                    posted_at = parsedate_to_datetime(pub_date).astimezone(UTC)
                except Exception:
                    pass

            postings.append(
                JobPosting(
                    id=uid,
                    title=title,
                    company="Upwork Client",
                    url=link,
                    location="Remote",
                    body=f"{title}\n{desc}",
                    posted_at=posted_at,
                    source=self.name,
                )
            )

        return postings
