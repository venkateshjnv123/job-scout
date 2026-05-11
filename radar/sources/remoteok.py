"""RemoteOK source — https://remoteok.com/api (JSON array)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_API_URL = "https://remoteok.com/api"


class RemoteOKSource(Source):
    """Fetches remote job listings from RemoteOK public API."""

    name = "remoteok"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        resp = await client.get(
            _API_URL,
            timeout=10.0,
            headers={"User-Agent": "job-radar/0.1 (github.com/venkateshjnv123/job-radar)"},
        )
        resp.raise_for_status()
        data = resp.json()

        # Index 0 is metadata object, skip it
        postings: list[JobPosting] = []
        for item in data[1:]:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
            if not url:
                continue
            uid = hashlib.md5(url.encode()).hexdigest()

            date_str = item.get("date")
            posted_at: datetime | None = None
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

            postings.append(
                JobPosting(
                    id=uid,
                    title=item.get("position") or "Software Engineer",
                    company=item.get("company") or "Unknown",
                    url=url,
                    location=item.get("location") or "Remote",
                    body=item.get("description") or "",
                    posted_at=posted_at,
                    source=self.name,
                )
            )
        return postings
