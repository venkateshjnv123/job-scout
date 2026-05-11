"""Jobicy remote jobs source — public JSON API, no auth, contract/part-time."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_API_URL = "https://jobicy.com/api/v2/remote-jobs"
_TAGS = ["java", "backend", "python", "machine-learning", "data-science"]


class JobicySource(Source):
    name = "jobicy"
    track = "gig"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        seen: set[str] = set()
        postings: list[JobPosting] = []
        for tag in _TAGS:
            try:
                postings.extend(await self._fetch_tag(client, tag, seen))
            except Exception:
                pass
        return postings

    async def _fetch_tag(
        self, client: httpx.AsyncClient, tag: str, seen: set[str]
    ) -> list[JobPosting]:
        resp = await client.get(
            _API_URL,
            params={"count": 50, "tag": tag},
            timeout=15.0,
        )
        resp.raise_for_status()

        jobs = resp.json().get("jobs", [])
        postings: list[JobPosting] = []

        for job in jobs:
            url = (job.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)

            uid = hashlib.md5(url.encode()).hexdigest()
            title = job.get("jobTitle") or ""
            company = job.get("companyName") or "Unknown"
            location = job.get("jobGeo") or "Remote"
            body = "\n".join(
                p for p in [title, job.get("jobExcerpt") or "", job.get("jobDescription") or ""] if p
            )

            posted_at: datetime | None = None
            pub_date = job.get("pubDate")
            if pub_date:
                try:
                    posted_at = datetime.fromisoformat(pub_date).replace(tzinfo=UTC)
                except Exception:
                    pass

            postings.append(
                JobPosting(
                    id=uid,
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    body=body,
                    posted_at=posted_at,
                    source=self.name,
                )
            )

        return postings
