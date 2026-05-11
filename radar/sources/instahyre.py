"""Instahyre source — cookie-based auth (sessionid + cf_clearance). Skips gracefully if absent."""

from __future__ import annotations

import hashlib

import httpx
import structlog

from radar.models import JobPosting
from radar.sources.base import Source

_API_URL = "https://www.instahyre.com/api/v1/job_search"
_PAGE_SIZE = 35
_MAX_PAGES = 5

log = structlog.get_logger()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instahyre.com/candidate/opportunities/",
}


class InstaHyreSource(Source):
    """Fetches job listings from Instahyre (Indian market) using session cookies."""

    name = "instahyre"

    def __init__(self, token: str = "", cookies: str = "") -> None:
        self._token = token      # legacy, unused
        self._cookies = cookies

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        if not self._cookies:
            log.info("instahyre_skipped", reason="INSTAHYRE_COOKIES not set")
            return []

        headers = {**_HEADERS, "Cookie": self._cookies}
        postings: list[JobPosting] = []

        for page in range(_MAX_PAGES):
            resp = await client.get(
                _API_URL,
                params={"limit": _PAGE_SIZE, "offset": page * _PAGE_SIZE},
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            objects = data.get("objects", [])
            if not objects:
                break

            for item in objects:
                url = item.get("public_url", "")
                if not url:
                    continue
                uid = hashlib.md5(url.encode()).hexdigest()

                keywords: list[str] = item.get("keywords") or []
                title: str = item.get("title") or "Software Engineer"
                employer = item.get("employer") or {}
                company: str = employer.get("company_name") or "Unknown"
                location: str = item.get("locations") or "India"

                # keywords is the structured skill list — use as body for scoring
                body = f"{title} {' '.join(keywords)}"

                postings.append(
                    JobPosting(
                        id=uid,
                        title=title,
                        company=company,
                        url=url,
                        location=location,
                        body=body,
                        posted_at=None,
                        source=self.name,
                    )
                )

        return postings
