"""Abstract base class for all job sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
import structlog

from radar.models import JobPosting

log = structlog.get_logger()

TIMEOUT = 10.0


class Source(ABC):
    """Base class for a job posting source.

    Subclasses implement `_fetch` with the source-specific logic.
    This class wraps it with timeout handling and fail-open error recovery.
    """

    name: str = "base"

    async def fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        """Fetch postings, returning empty list on any failure (fail-open)."""
        try:
            postings = await self._fetch(client)
            log.info("source_fetched", source=self.name, count=len(postings))
            return postings
        except httpx.TimeoutException:
            log.warning("source_timeout", source=self.name)
            return []
        except httpx.HTTPStatusError as e:
            log.warning("source_http_error", source=self.name, status=e.response.status_code)
            return []
        except Exception as e:
            log.warning("source_error", source=self.name, error=str(e))
            return []

    @abstractmethod
    async def _fetch(self, client: httpx.AsyncClient) -> list[JobPosting]:
        """Source-specific fetch logic. Must be implemented by subclasses."""
        ...
