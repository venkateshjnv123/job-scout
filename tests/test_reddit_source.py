"""Tests for the Reddit source."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from radar.sources.reddit import RedditSource, _parse_title

_FORHIRE_URL = "https://www.reddit.com/r/forhire/search.json"
_REMOTEWORK_URL = "https://www.reddit.com/r/remotework/search.json"

_HIRING_POST = {
    "kind": "t3",
    "data": {
        "id": "abc123",
        "title": "[Hiring] Backend Engineer | Acme Corp | Remote | Java/Kafka",
        "selftext": "We need a backend engineer with 2-4 years Java and Kafka experience.",
        "url": "https://www.reddit.com/r/forhire/comments/abc123/hiring_backend/",
        "permalink": "/r/forhire/comments/abc123/hiring_backend/",
        "link_flair_text": "Hiring",
        "created_utc": 1746748800.0,
    },
}

_NON_HIRING_POST = {
    "kind": "t3",
    "data": {
        "id": "def456",
        "title": "[For Hire] Frontend dev available",
        "selftext": "I am available for freelance work.",
        "url": "https://www.reddit.com/r/forhire/comments/def456/",
        "permalink": "/r/forhire/comments/def456/",
        "link_flair_text": "For Hire",
        "created_utc": 1746748800.0,
    },
}


def _reddit_response(posts: list[dict]) -> dict:
    return {"data": {"children": posts}}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_hiring_posts() -> None:
    respx.get(_FORHIRE_URL).mock(
        return_value=httpx.Response(200, json=_reddit_response([_HIRING_POST]))
    )
    respx.get(_REMOTEWORK_URL).mock(
        return_value=httpx.Response(200, json=_reddit_response([]))
    )

    async with httpx.AsyncClient() as client:
        posts = await RedditSource()._fetch(client)

    assert len(posts) == 1
    assert posts[0].title == "Backend Engineer"
    assert posts[0].company == "Acme Corp"
    assert posts[0].location == "Remote"
    assert posts[0].source == "reddit"


@pytest.mark.asyncio
@respx.mock
async def test_non_hiring_posts_excluded() -> None:
    respx.get(_FORHIRE_URL).mock(
        return_value=httpx.Response(200, json=_reddit_response([_NON_HIRING_POST]))
    )
    respx.get(_REMOTEWORK_URL).mock(
        return_value=httpx.Response(200, json=_reddit_response([]))
    )

    async with httpx.AsyncClient() as client:
        posts = await RedditSource()._fetch(client)

    assert len(posts) == 0


@pytest.mark.asyncio
@respx.mock
async def test_source_fails_open_on_error() -> None:
    respx.get(_FORHIRE_URL).mock(return_value=httpx.Response(429))
    respx.get(_REMOTEWORK_URL).mock(return_value=httpx.Response(429))

    async with httpx.AsyncClient() as client:
        posts = await RedditSource().fetch(client)

    assert posts == []


@pytest.mark.asyncio
@respx.mock
async def test_deduplicates_same_url() -> None:
    dupe = _HIRING_POST.copy()
    respx.get(_FORHIRE_URL).mock(
        return_value=httpx.Response(200, json=_reddit_response([_HIRING_POST, dupe]))
    )
    respx.get(_REMOTEWORK_URL).mock(
        return_value=httpx.Response(200, json=_reddit_response([]))
    )

    async with httpx.AsyncClient() as client:
        posts = await RedditSource()._fetch(client)

    # Same URL → same MD5 id; both appear (dedup is SeenStore's job, not source's)
    assert len(posts) == 2
    assert posts[0].id == posts[1].id  # same hash


# --- unit tests for title parser ---

def test_parse_title_full_format() -> None:
    title, company, loc = _parse_title("[Hiring] Backend Dev | Stripe | Remote | $120k")
    assert title == "Backend Dev"
    assert company == "Stripe"
    assert loc == "Remote"


def test_parse_title_no_pipes() -> None:
    title, company, loc = _parse_title("[Hiring] Software Engineer at Google")
    assert title == "Software Engineer at Google"
    assert company == "Unknown"
    assert loc == "Remote"


def test_parse_title_for_hire_prefix() -> None:
    title, company, loc = _parse_title("[For Hire] Full Stack Dev | Freelance | Worldwide")
    assert title == "Full Stack Dev"
    assert company == "Freelance"
    assert loc == "Worldwide"


def test_parse_title_no_prefix() -> None:
    title, company, loc = _parse_title("Backend Engineer | Acme | Hyderabad")
    assert title == "Backend Engineer"
    assert company == "Acme"
    assert loc == "Hyderabad"
