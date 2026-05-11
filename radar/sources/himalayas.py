"""Himalayas remote jobs source — public JSON API, no auth."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_API_URL = "https://himalayas.app/jobs/api"
_PAGE_SIZE = 100
_MAX_PAGES = 3


class HimalayasSource(Source):
    name = "himalayas"
    track = "gig"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        seen: set[str] = set()
        postings: list[JobPosting] = []
        for page in range(_MAX_PAGES):
            batch, done = await self._fetch_page(client, page * _PAGE_SIZE, seen)
            postings.extend(batch)
            if done:
                break
        return postings

    async def _fetch_page(
        self, client: httpx.AsyncClient, offset: int, seen: set[str]
    ) -> tuple[list[JobPosting], bool]:
        resp = await client.get(
            _API_URL,
            params={"limit": _PAGE_SIZE, "offset": offset},
            timeout=15.0,
        )
        resp.raise_for_status()

        data = resp.json()
        jobs = data.get("jobs", [])
        if not jobs:
            return [], True

        postings: list[JobPosting] = []
        for job in jobs:
            url = (job.get("applicationLink") or "").strip()
            if not url:
                slug = job.get("guid") or ""
                url = f"https://himalayas.app/jobs/{slug}" if slug else ""
            if not url or url in seen:
                continue
            seen.add(url)

            uid = hashlib.md5(url.encode()).hexdigest()
            title = job.get("title") or ""
            company = job.get("companyName") or "Unknown"
            locs = job.get("locationRestrictions") or []
            location = ", ".join(locs) if locs else "Remote"
            body = "\n".join(p for p in [title, job.get("description") or ""] if p)

            posted_at: datetime | None = None
            pub_date = job.get("pubDate")
            if pub_date:
                try:
                    posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
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

        return postings, len(jobs) < _PAGE_SIZE
