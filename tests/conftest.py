"""Shared fixtures for all tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from radar.models import JobPosting, ResumeProfile

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_resume_path() -> Path:
    return FIXTURES_DIR / "sample_resume.pdf"


@pytest.fixture
def sample_profile() -> ResumeProfile:
    return ResumeProfile(
        name="Venkatesh Patnala",
        raw_text="Java Spring Boot Kafka PostgreSQL Redis Microservices AWS 2 years experience",
        skills=["Java", "Spring Boot", "Kafka", "PostgreSQL", "Redis", "Microservices", "AWS"],
        yoe=2,
    )


@pytest.fixture
def backend_posting() -> JobPosting:
    return JobPosting(
        id="test-001",
        title="Backend Software Engineer",
        company="Acme Corp",
        url="https://example.com/job/1",
        location="Remote",
        body=(
            "We are looking for a backend engineer with 2-4 years of experience. "
            "You will work with Java, Spring Boot, Kafka, and PostgreSQL in a microservices "
            "architecture. Remote position open to candidates in India."
        ),
        posted_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        source="hn_hiring",
    )


@pytest.fixture
def senior_posting() -> JobPosting:
    return JobPosting(
        id="test-002",
        title="Senior Backend Engineer",
        company="BigCo",
        url="https://example.com/job/2",
        location="Remote",
        body="Senior engineer needed. 7+ years of experience required. Java, Spring Boot.",
        posted_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        source="hn_hiring",
    )


@pytest.fixture
def onsite_posting() -> JobPosting:
    return JobPosting(
        id="test-003",
        title="Software Engineer",
        company="LocalCo",
        url="https://example.com/job/3",
        location="New York",
        body="Onsite role in New York. Java developer needed.",
        posted_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        source="hn_hiring",
    )
