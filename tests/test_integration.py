"""End-to-end integration tests using respx to mock all HTTP sources."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from radar.dedup import SeenStore
from radar.filters import apply_filters
from radar.models import JobPosting
from radar.scoring.rule_based import score_jobs
from radar.sources.hn_hiring import HNHiringSource
from radar.sources.instahyre import InstaHyreSource
from radar.sources.remoteok import RemoteOKSource
from radar.sources.remotive import RemotiveSource
from radar.sources.weworkremotely import WeWorkRemotelySource

FIXTURES = Path(__file__).parent / "fixtures"

_SKILL_WEIGHTS = {
    "java": 10,
    "spring": 10,
    "spring_boot": 10,
    "kafka": 7,
    "postgres": 5,
    "microservices": 8,
    "redis": 5,
    "aws": 5,
}
_LOCATIONS = ["remote", "hyderabad", "bangalore"]
_MUST_NOT = ["senior", "staff", "principal", "lead", "director", "5+ years", "7+ years"]
_YOE_TARGET = [2, 4]


# ── Individual source tests ──────────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_remoteok_source() -> None:
    fixture = json.loads((FIXTURES / "remoteok_response.json").read_text())
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=fixture))

    async with httpx.AsyncClient() as client:
        postings = await RemoteOKSource().fetch(client)

    assert len(postings) == 2
    assert postings[0].source == "remoteok"
    assert postings[0].title == "Backend Software Engineer"
    assert postings[0].company == "RemoteCo"


@respx.mock
@pytest.mark.asyncio
async def test_remotive_source() -> None:
    fixture = json.loads((FIXTURES / "remotive_response.json").read_text())
    respx.get("https://remotive.com/api/remote-jobs").mock(return_value=httpx.Response(200, json=fixture))

    async with httpx.AsyncClient() as client:
        postings = await RemotiveSource().fetch(client)

    assert len(postings) == 2
    assert postings[0].source == "remotive"
    assert postings[0].title == "Backend Engineer"
    assert "India" in postings[0].location or "Remote" in postings[0].location


@respx.mock
@pytest.mark.asyncio
async def test_weworkremotely_source() -> None:
    fixture_xml = (FIXTURES / "weworkremotely_response.xml").read_text()
    respx.get(
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"
    ).mock(return_value=httpx.Response(200, text=fixture_xml))

    async with httpx.AsyncClient() as client:
        postings = await WeWorkRemotelySource().fetch(client)

    assert len(postings) == 2
    assert postings[0].source == "weworkremotely"
    assert postings[0].company == "TechStartup"
    assert postings[0].title == "Backend Java Engineer"


@pytest.mark.asyncio
async def test_instahyre_skips_without_token() -> None:
    async with httpx.AsyncClient() as client:
        postings = await InstaHyreSource(token="").fetch(client)
    assert postings == []


@respx.mock
@pytest.mark.asyncio
async def test_instahyre_with_token() -> None:
    fixture = {
        "results": [
            {
                "id": 1,
                "designation": "Backend Engineer",
                "company": {"name": "TechIndia"},
                "url_string": "backend-engineer-techindia",
                "location": "Hyderabad",
                "description": "Java Spring Boot microservices 2-3 years",
            }
        ]
    }
    respx.get("https://www.instahyre.com/api/v1/opportunity/").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    async with httpx.AsyncClient() as client:
        postings = await InstaHyreSource(token="fake-token").fetch(client)

    assert len(postings) == 1
    assert postings[0].company == "TechIndia"
    assert postings[0].location == "Hyderabad"


@respx.mock
@pytest.mark.asyncio
async def test_hn_source_mocked() -> None:
    thread_fixture = json.loads((FIXTURES / "hn_thread_response.json").read_text())
    comments_fixture = json.loads((FIXTURES / "hn_comments_response.json").read_text())

    respx.get("https://hn.algolia.com/api/v1/search", params__contains={"query": "Ask HN: Who is hiring?"}).mock(
        return_value=httpx.Response(200, json=thread_fixture)
    )
    respx.get("https://hn.algolia.com/api/v1/search", params__contains={"tags": "comment,story_41234567"}).mock(
        return_value=httpx.Response(200, json=comments_fixture)
    )

    async with httpx.AsyncClient() as client:
        postings = await HNHiringSource().fetch(client)

    assert len(postings) == 2
    assert postings[0].source == "hn_hiring"


# ── Fail-open tests ──────────────────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_source_timeout_returns_empty() -> None:
    respx.get("https://remoteok.com/api").mock(side_effect=httpx.TimeoutException("timeout"))
    async with httpx.AsyncClient() as client:
        postings = await RemoteOKSource().fetch(client)
    assert postings == []


@respx.mock
@pytest.mark.asyncio
async def test_source_http_error_returns_empty() -> None:
    respx.get("https://remotive.com/api/remote-jobs").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        postings = await RemotiveSource().fetch(client)
    assert postings == []


# ── Full pipeline integration test ───────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_full_pipeline_remoteok_to_scored(tmp_path: Path) -> None:
    """Fetch → dedup → filter → score — end-to-end with mocked HTTP."""
    fixture = json.loads((FIXTURES / "remoteok_response.json").read_text())
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=fixture))

    async with httpx.AsyncClient() as client:
        postings = await RemoteOKSource().fetch(client)

    # Dedup
    db = str(tmp_path / "seen.db")
    with SeenStore(db) as store:
        new_postings = store.filter_new(postings)
    assert len(new_postings) == len(postings)

    # Filter
    filtered = apply_filters(new_postings, _LOCATIONS, _MUST_NOT)
    # Senior posting should be dropped
    assert all("senior" not in p.title.lower() for p in filtered)

    # Score
    scored = score_jobs(filtered, _SKILL_WEIGHTS, _YOE_TARGET, min_score=0, top_n=10)
    assert len(scored) > 0
    # Backend Engineer posting should score higher than 0
    assert scored[0].score > 0

    # Mark seen
    with SeenStore(db) as store:
        store.mark_seen([s.posting for s in scored])
        # Second pass — all should be filtered by dedup
        second_pass = store.filter_new(postings)

    seen_urls = {s.posting.url for s in scored}
    for p in second_pass:
        assert p.url not in seen_urls


@respx.mock
@pytest.mark.asyncio
async def test_markdown_output_written(tmp_path: Path) -> None:
    """Full pipeline writes markdown digest to disk."""
    from datetime import date

    from radar.output.markdown import write_digest

    fixture = json.loads((FIXTURES / "remoteok_response.json").read_text())
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=fixture))

    async with httpx.AsyncClient() as client:
        postings = await RemoteOKSource().fetch(client)

    filtered = apply_filters(postings, _LOCATIONS, _MUST_NOT)
    scored = score_jobs(filtered, _SKILL_WEIGHTS, _YOE_TARGET, min_score=0, top_n=10)

    out_path = write_digest(
        scored,
        total_scored=len(postings),
        total_passed=len(filtered),
        output_dir=str(tmp_path / "digests"),
        run_date=date(2026, 5, 4),
    )

    assert out_path.exists()
    content = out_path.read_text()
    assert "2026-05-04" in content
    assert "RemoteCo" in content
