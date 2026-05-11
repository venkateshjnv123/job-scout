"""Tests for the filters module."""

from __future__ import annotations

from radar.filters import apply_filters, _has_high_yoe_requirement, _matches_seniority_block
from radar.models import JobPosting


_LOCATIONS = ["remote", "hyderabad", "bangalore"]
_MUST_NOT = ["senior", "staff", "principal", "lead", "director", "5+ years", "7+ years"]


def test_remote_job_passes(backend_posting: JobPosting) -> None:
    result = apply_filters([backend_posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 1


def test_onsite_job_dropped(onsite_posting: JobPosting) -> None:
    result = apply_filters([onsite_posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 0


def test_senior_title_dropped(senior_posting: JobPosting) -> None:
    result = apply_filters([senior_posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 0


def test_hyderabad_location_passes(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(update={"location": "Hyderabad, India"})
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 1


def test_bangalore_location_passes(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(
        update={"location": "Bangalore", "body": backend_posting.body}
    )
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 1


def test_principal_in_title_dropped(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(update={"title": "Principal Engineer"})
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 0


def test_lead_in_title_dropped(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(update={"title": "Lead Backend Engineer"})
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 0


def test_high_yoe_in_body_dropped(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(
        update={"body": "Remote job. Java required. 7+ years of experience required."}
    )
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 0


def test_five_plus_years_dropped(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(
        update={"body": "Remote backend role. 5+ years experience in Java."}
    )
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 0


def test_three_years_passes(backend_posting: JobPosting) -> None:
    posting = backend_posting.model_copy(
        update={"body": "Remote role. 2-3 years of experience. Java Spring Boot. Remote India."}
    )
    result = apply_filters([posting], _LOCATIONS, _MUST_NOT)
    assert len(result) == 1


def test_seniority_block_staff() -> None:
    posting = JobPosting(
        id="x", title="Staff Engineer", company="Co", url="http://x.com",
        location="Remote", body="Remote India Java role", source="test"
    )
    assert _matches_seniority_block(posting, _MUST_NOT) is True


def test_high_yoe_10_years() -> None:
    posting = JobPosting(
        id="x", title="Engineer", company="Co", url="http://x.com",
        location="Remote", body="10 years experience required", source="test"
    )
    assert _has_high_yoe_requirement(posting) is True


def test_multiple_postings_mixed(
    backend_posting: JobPosting, senior_posting: JobPosting, onsite_posting: JobPosting
) -> None:
    result = apply_filters(
        [backend_posting, senior_posting, onsite_posting], _LOCATIONS, _MUST_NOT
    )
    assert len(result) == 1
    assert result[0].id == backend_posting.id
