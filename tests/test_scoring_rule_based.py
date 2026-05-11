"""Tests for rule-based scorer."""

from __future__ import annotations

from radar.models import JobPosting
from radar.scoring.rule_based import (
    _extract_yoe_range,
    _score_role_fit,
    _score_skills,
    _score_yoe_band,
    score_job,
    score_jobs,
)

_WEIGHTS = {
    "java": 10,
    "spring": 10,
    "spring_boot": 10,
    "kafka": 7,
    "rabbitmq": 5,
    "postgres": 5,
    "redis": 5,
    "microservices": 8,
    "aws": 5,
    "system_design": 5,
}
_YOE_TARGET = [2, 4]


def test_skill_score_java_spring() -> None:
    score, matched = _score_skills("Java Spring Boot developer", _WEIGHTS)
    assert score > 0
    assert "java" in matched or "spring" in matched


def test_skill_score_capped_at_60() -> None:
    text = "java spring spring_boot kafka rabbitmq postgres redis microservices aws system_design"
    score, _ = _score_skills(text, _WEIGHTS)
    assert score <= 60


def test_skill_score_no_match() -> None:
    score, matched = _score_skills("Python React developer", _WEIGHTS)
    assert score == 0
    assert matched == []


def test_role_fit_backend_title() -> None:
    score = _score_role_fit("Backend Software Engineer", "We build distributed systems")
    assert score >= 15


def test_role_fit_sde_title() -> None:
    score = _score_role_fit("SDE 2", "scalable microservices")
    assert score >= 15


def test_role_fit_no_match() -> None:
    score = _score_role_fit("Data Scientist", "ML models and pipelines")
    assert score == 0


def test_yoe_extract_simple() -> None:
    lo, hi = _extract_yoe_range("2+ years experience")
    assert lo == 2


def test_yoe_extract_range() -> None:
    lo, hi = _extract_yoe_range("2 to 4 years of experience")
    assert lo == 2
    assert hi == 4


def test_yoe_extract_none() -> None:
    lo, hi = _extract_yoe_range("No experience requirement")
    assert lo is None
    assert hi is None


def test_yoe_band_in_range() -> None:
    score = _score_yoe_band("2 to 4 years experience required", _YOE_TARGET)
    assert score == 15


def test_yoe_band_unspecified() -> None:
    score = _score_yoe_band("No experience mentioned", _YOE_TARGET)
    assert score == 10


def test_yoe_band_outside() -> None:
    score = _score_yoe_band("8 to 10 years experience", _YOE_TARGET)
    assert score == 0


def test_score_job_full(backend_posting: JobPosting) -> None:
    result = score_job(backend_posting, _WEIGHTS, _YOE_TARGET)
    assert result.score > 0
    assert result.score <= 100
    assert "skill_score" in result.breakdown
    assert "role_score" in result.breakdown
    assert "yoe_score" in result.breakdown


def test_score_job_high_match(backend_posting: JobPosting) -> None:
    result = score_job(backend_posting, _WEIGHTS, _YOE_TARGET)
    # backend posting has java, spring boot, kafka, postgres, microservices, remote
    assert result.score >= 40


def test_score_jobs_filters_min_score() -> None:
    low = JobPosting(
        id="low", title="ML Engineer", company="Co", url="http://x.com/low",
        location="Remote", body="Python TensorFlow deep learning", source="test"
    )
    high = JobPosting(
        id="high", title="Backend Software Engineer", company="Co", url="http://x.com/high",
        location="Remote",
        body="Java Spring Boot Kafka microservices 2-4 years experience remote",
        source="test"
    )
    results = score_jobs([low, high], _WEIGHTS, _YOE_TARGET, min_score=40, top_n=10)
    ids = [r.posting.id for r in results]
    assert "high" in ids


def test_score_jobs_sorted_descending() -> None:
    postings = [
        JobPosting(
            id=f"job-{i}", title="Backend Engineer", company="Co",
            url=f"http://x.com/{i}", location="Remote",
            body=f"java spring boot microservices {i} years experience remote india",
            source="test"
        )
        for i in range(1, 6)
    ]
    results = score_jobs(postings, _WEIGHTS, _YOE_TARGET, min_score=0, top_n=10)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_score_jobs_respects_top_n() -> None:
    postings = [
        JobPosting(
            id=f"job-{i}", title="Backend Software Engineer", company="Co",
            url=f"http://x.com/{i}", location="Remote",
            body="java spring kafka microservices remote india 2 years",
            source="test"
        )
        for i in range(20)
    ]
    results = score_jobs(postings, _WEIGHTS, _YOE_TARGET, min_score=0, top_n=5)
    assert len(results) <= 5
