"""HN Who's Hiring source — queries Algolia HN Search API."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
_HIRING_THREAD_QUERY = "Ask HN: Who is hiring?"


class HNHiringSource(Source):
    """Fetches job comments from monthly HN 'Who is hiring?' threads."""

    name = "hn_hiring"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        thread_id = await self._get_latest_thread_id(client)
        if not thread_id:
            return []
        return await self._get_job_comments(client, thread_id)

    async def _get_latest_thread_id(self, client: httpx.AsyncClient) -> str | None:
        """Get the story ID of the most recent Who is Hiring thread."""
        resp = await client.get(
            _ALGOLIA_URL,
            params={
                "query": _HIRING_THREAD_QUERY,
                "tags": "story,ask_hn",
                "hitsPerPage": 1,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if not hits:
            return None
        return str(hits[0]["objectID"])

    async def _get_job_comments(
        self, client: httpx.AsyncClient, thread_id: str
    ) -> list[JobPosting]:
        """Fetch top-level comments (job postings) from a hiring thread."""
        resp = await client.get(
            _ALGOLIA_URL,
            params={
                "tags": f"comment,story_{thread_id}",
                "hitsPerPage": 200,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        postings: list[JobPosting] = []

        for hit in hits:
            text: str = hit.get("comment_text") or ""
            if not text.strip():
                continue

            object_id: str = hit.get("objectID", "")
            url = f"https://news.ycombinator.com/item?id={object_id}"
            uid = hashlib.md5(url.encode()).hexdigest()

            # First line of comment is usually "Company | Role | Location | ..."
            first_line = text.split("\n")[0].replace("<p>", "").strip()
            parts = [p.strip() for p in first_line.split("|")]
            company = parts[0] if parts else "Unknown"
            title = parts[1] if len(parts) > 1 else "Software Engineer"
            location = parts[2] if len(parts) > 2 else "Unknown"

            created_at = hit.get("created_at")
            posted_at: datetime | None = None
            if created_at:
                try:
                    posted_at = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    posted_at = None

            postings.append(
                JobPosting(
                    id=uid,
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    body=text,
                    posted_at=posted_at,
                    source=self.name,
                )
            )

        return postings
