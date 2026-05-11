"""Findwork.dev source — token auth, global tech jobs with India coverage."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

import httpx
import structlog

from radar.models import JobPosting
from radar.sources.base import Source

_API_URL = "https://findwork.dev/api/jobs/"
_SEARCHES = ["java spring backend", "java microservices", "java kafka backend"]
_PAGE_SIZE = 50

log = structlog.get_logger()

_HTML_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAGS.sub(" ", text)


class FindworkSource(Source):
    """Fetches tech jobs from Findwork.dev API."""

    name = "findwork"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        if not self._api_key:
            log.info("findwork_skipped", reason="FINDWORK_API_KEY not set")
            return []

        headers = {"Authorization": f"Token {self._api_key}"}
        seen_ids: set[str] = set()
        postings: list[JobPosting] = []

        for query in _SEARCHES:
            resp = await client.get(
                _API_URL,
                params={"search": query, "limit": _PAGE_SIZE},
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()

            for item in resp.json().get("results", []):
                uid = hashlib.md5(str(item.get("id", "")).encode()).hexdigest()
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)

                url: str = item.get("url") or ""
                if not url:
                    continue

                keywords: list[str] = item.get("keywords") or []
                text: str = _strip_html(item.get("text") or "")
                title: str = item.get("role") or "Software Engineer"
                company: str = item.get("company_name") or "Unknown"
                location: str = item.get("location") or ("Remote" if item.get("remote") else "")

                body = f"{title} {' '.join(keywords)} {text}"

                date_str: str = item.get("date_posted") or ""
                posted_at: datetime | None = None
                if date_str:
                    try:
                        posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except ValueError:
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
