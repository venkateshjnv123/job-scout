"""Reddit r/forhire source — public JSON API, no auth required."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx

from radar.models import JobPosting
from radar.sources.base import Source

_SUBREDDITS = ["forhire", "remotework"]
_BASE = "https://www.reddit.com/r/{sub}/search.json"
# Reddit hard-blocks requests without a descriptive User-Agent
_HEADERS = {"User-Agent": "job-radar/0.1 (github.com/venkateshjnv123/job-radar)"}


class RedditSource(Source):
    """Fetches [Hiring] posts from r/forhire and r/remotework."""

    name = "reddit"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        postings: list[JobPosting] = []
        for sub in _SUBREDDITS:
            postings.extend(await self._fetch_sub(client, sub))
        return postings

    async def _fetch_sub(self, client: httpx.AsyncClient, sub: str) -> list[JobPosting]:
        """Fetch hiring posts from a single subreddit."""
        resp = await client.get(
            _BASE.format(sub=sub),
            params={"q": "flair:Hiring", "restrict_sr": "1", "sort": "new", "limit": 100},
            headers=_HEADERS,
            timeout=10.0,
        )
        resp.raise_for_status()

        children = resp.json().get("data", {}).get("children", [])
        postings: list[JobPosting] = []

        for child in children:
            d = child.get("data", {})
            flair: str = (d.get("link_flair_text") or "").lower()
            title: str = d.get("title") or ""

            # Only hiring posts
            is_hiring = "hiring" in flair or title.lower().startswith("[hiring]")
            if not is_hiring:
                continue

            url: str = d.get("url") or f"https://www.reddit.com{d.get('permalink', '')}"
            if not url:
                continue

            uid = hashlib.md5(url.encode()).hexdigest()
            body: str = d.get("selftext") or ""
            clean_title, company, location = _parse_title(title)

            created_utc = d.get("created_utc")
            posted_at: datetime | None = None
            if created_utc:
                posted_at = datetime.fromtimestamp(float(created_utc), tz=UTC)

            postings.append(
                JobPosting(
                    id=uid,
                    title=clean_title,
                    company=company,
                    url=url,
                    location=location,
                    body=f"{clean_title}\n{body}",
                    posted_at=posted_at,
                    source=self.name,
                )
            )

        return postings


def _parse_title(raw: str) -> tuple[str, str, str]:
    """Parse r/forhire title format: [Hiring] Role | Company | Location | ...

    Returns (title, company, location). Falls back gracefully.
    """
    # Strip [Hiring] / [For Hire] prefix
    stripped = raw
    if stripped.upper().startswith("[HIRING]"):
        stripped = stripped[8:].strip()
    elif stripped.upper().startswith("[FOR HIRE]"):
        stripped = stripped[10:].strip()

    parts = [p.strip() for p in stripped.split("|")]

    title = parts[0] if parts else stripped
    company = parts[1] if len(parts) > 1 else "Unknown"
    location = parts[2] if len(parts) > 2 else "Remote"

    return title, company, location
