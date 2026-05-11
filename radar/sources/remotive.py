"""Remotive source — https://remotive.com/api/remote-jobs (JSON)."""

from __future__ import annotations

import hashlib
from datetime import datetime

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource(Source):
    """Fetches remote software jobs from Remotive public API."""

    name = "remotive"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        resp = await client.get(
            _API_URL,
            params={"category": "software-dev", "limit": 100},
            timeout=10.0,
        )
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])

        postings: list[JobPosting] = []
        for item in jobs:
            url = item.get("url") or ""
            if not url:
                continue
            uid = hashlib.md5(url.encode()).hexdigest()

            pub_date = item.get("publication_date")
            posted_at: datetime | None = None
            if pub_date:
                try:
                    posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

            postings.append(
                JobPosting(
                    id=uid,
                    title=item.get("title") or "Software Engineer",
                    company=item.get("company_name") or "Unknown",
                    url=url,
                    location=item.get("candidate_required_location") or "Remote",
                    body=item.get("description") or "",
                    posted_at=posted_at,
                    source=self.name,
                )
            )
        return postings
