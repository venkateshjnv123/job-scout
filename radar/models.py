"""Core domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class JobPosting(BaseModel):
    """A single job posting fetched from a source."""

    id: str
    title: str
    company: str
    url: str
    location: str
    body: str
    posted_at: datetime | None = None
    source: str
    track: str = "fulltime"


class ResumeProfile(BaseModel):
    """Parsed and normalised resume data."""

    name: str
    raw_text: str
    skills: list[str] = Field(default_factory=list)
    yoe: int | None = None


class ScoredJob(BaseModel):
    """A job posting with a computed match score."""

    posting: JobPosting
    score: int = Field(ge=0, le=100)
    breakdown: dict[str, Any] = Field(default_factory=dict)
    llm_verdict: str | None = None
    llm_matched_skills: list[str] = Field(default_factory=list)
    llm_gaps: list[str] = Field(default_factory=list)
    llm_pitch: str | None = None
    llm_resume_emphasis: str | None = None
