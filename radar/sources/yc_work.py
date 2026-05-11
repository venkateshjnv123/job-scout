"""YC Work at a Startup source — scrapes workatastartup.com with selectolax."""

from __future__ import annotations

import hashlib
import re

import httpx
import structlog
from selectolax.parser import HTMLParser

from radar.models import JobPosting
from radar.sources.base import Source

_URL = "https://www.workatastartup.com/jobs"
log = structlog.get_logger()


class YCWorkSource(Source):
    """Fetches backend job listings from Y Combinator's Work at a Startup board."""

    name = "yc_work"

    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        resp = await client.get(
            _URL,
            params={"role": "eng", "remote": "only"},
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        resp.raise_for_status()
        return self._parse(resp.text)

    def _parse(self, html: str) -> list[JobPosting]:
        tree = HTMLParser(html)
        postings: list[JobPosting] = []

        # Job listings are anchor tags with href matching /jobs/<id>
        seen_urls: set[str] = set()
        for node in tree.css("a[href*='/jobs/']"):
            href = node.attributes.get("href", "")
            if not re.match(r"^/jobs/\d+", href):
                continue
            url = f"https://www.workatastartup.com{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            uid = hashlib.md5(url.encode()).hexdigest()

            # Extract text content for title, company, location heuristically
            text = node.text(strip=True)
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            title = lines[0] if lines else "Software Engineer"
            company = lines[1] if len(lines) > 1 else "YC Startup"
            location = lines[2] if len(lines) > 2 else "Remote"
            body = " ".join(lines)

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

        log.debug("yc_work_parsed", count=len(postings))
        return postings
