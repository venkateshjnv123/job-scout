"""Hard filters — drop jobs that don't match location, title, or YoE band."""

from __future__ import annotations

import re

import structlog

from radar.models import JobPosting

log = structlog.get_logger()

_SENIORITY_TITLES = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|sr[-\s]staff|head\s+of|vp|vice\s+president)\b",
    re.IGNORECASE,
)

_HIGH_YOE = re.compile(
    r"\b([5-9]\d*|\d{2,})\s*\+\s*years?\b"
    r"|\b(5|6|7|8|9|10|11|12|13|14|15)\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?(?:experience)?\b",
    re.IGNORECASE,
)


def _matches_location(posting: JobPosting, locations: list[str]) -> bool:
    """Return True if posting location matches any configured target."""
    text = (posting.location + " " + posting.body).lower()
    return any(loc.lower() in text for loc in locations)


def _matches_seniority_block(posting: JobPosting, must_not_match: list[str]) -> bool:
    """Return True if title or body contains a blocked seniority keyword."""
    title_lower = posting.title.lower()
    body_lower = posting.body.lower()
    for term in must_not_match:
        if term.lower() in title_lower or term.lower() in body_lower:
            return True
    if _SENIORITY_TITLES.search(posting.title):
        return True
    return False


def _has_high_yoe_requirement(posting: JobPosting) -> bool:
    """Return True if JD explicitly requires 5+ years."""
    return bool(_HIGH_YOE.search(posting.body))


def apply_filters(
    postings: list[JobPosting],
    locations: list[str],
    must_not_match: list[str],
) -> list[JobPosting]:
    """Apply all hard filters, returning only passing postings."""
    passed: list[JobPosting] = []
    dropped_location = dropped_seniority = dropped_yoe = 0

    for p in postings:
        if not _matches_location(p, locations):
            dropped_location += 1
            continue
        if _matches_seniority_block(p, must_not_match):
            dropped_seniority += 1
            continue
        if _has_high_yoe_requirement(p):
            dropped_yoe += 1
            continue
        passed.append(p)

    log.info(
        "filters_applied",
        total=len(postings),
        passed=len(passed),
        dropped_location=dropped_location,
        dropped_seniority=dropped_seniority,
        dropped_yoe=dropped_yoe,
    )
    return passed
