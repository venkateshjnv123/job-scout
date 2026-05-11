"""Tests for resume parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from radar.resume.parser import _extract_skills, _extract_yoe, parse_resume


def test_extract_skills_finds_java() -> None:
    text = "Experienced Java and Spring Boot developer with Kafka expertise"
    skills = _extract_skills(text)
    assert "java" in [s.lower() for s in skills] or "Java" in skills


def test_extract_skills_case_insensitive() -> None:
    text = "JAVA SPRING KAFKA POSTGRESQL"
    skills = _extract_skills(text)
    assert len(skills) >= 3


def test_extract_skills_no_false_positives() -> None:
    text = "I love cooking pasta and hiking mountains"
    skills = _extract_skills(text)
    assert skills == []


def test_extract_yoe_simple() -> None:
    assert _extract_yoe("2 years of experience") == 2


def test_extract_yoe_range() -> None:
    # Should return the max found
    result = _extract_yoe("3 to 5 years experience")
    assert result is not None
    assert result >= 3


def test_extract_yoe_none() -> None:
    assert _extract_yoe("No experience mentioned") is None


def test_extract_yoe_takes_max() -> None:
    result = _extract_yoe("1 year at first job, 3 years at second job")
    assert result == 3


def test_parse_resume_pdf(sample_resume_path: Path) -> None:
    if not sample_resume_path.exists():
        pytest.skip("sample_resume.pdf not found in fixtures")
    profile = parse_resume(str(sample_resume_path), name="Venkatesh")
    assert profile.name == "Venkatesh"
    assert len(profile.raw_text) > 100
    assert len(profile.skills) > 0


def test_parse_resume_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        parse_resume("/nonexistent/path/resume.pdf")


def test_parse_resume_unsupported_format(tmp_path: Path) -> None:
    f = tmp_path / "resume.txt"
    f.write_text("some text")
    with pytest.raises(ValueError, match="Unsupported resume format"):
        parse_resume(str(f))
