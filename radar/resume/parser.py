"""Resume parser — extracts text and skills from PDF or DOCX."""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from radar.models import ResumeProfile
from radar.resume.normalizer import dedupe_skills

log = structlog.get_logger()

_SKILL_KEYWORDS: list[str] = [
    "java", "spring", "spring boot", "springboot", "kafka", "rabbitmq",
    "postgres", "postgresql", "redis", "aws", "microservices", "kubernetes",
    "k8s", "docker", "mysql", "mongodb", "elasticsearch", "rest", "grpc",
    "graphql", "hibernate", "jpa", "maven", "gradle", "git", "ci/cd",
    "system design", "distributed", "scalable", "multithreading", "concurrency",
    "python", "go", "golang", "node", "nodejs", "typescript",
]

_YOE_PATTERN = re.compile(
    r"(\d+)\s*\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?(?:experience)?",
    re.IGNORECASE,
)


def _extract_text_pdf(path: Path) -> str:
    """Extract raw text from PDF using pdfplumber."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def _extract_text_docx(path: Path) -> str:
    """Extract raw text from DOCX."""
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_skills(text: str) -> list[str]:
    """Find skill keywords present in resume text."""
    text_lower = text.lower()
    found: list[str] = []
    for skill in _SKILL_KEYWORDS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return dedupe_skills(found)


def _extract_yoe(text: str) -> int | None:
    """Infer years of experience from resume text (takes max match)."""
    matches = _YOE_PATTERN.findall(text)
    if not matches:
        return None
    years = [int(m) for m in matches if int(m) < 40]
    return max(years) if years else None


def parse_resume(path: str | Path, name: str = "Candidate") -> ResumeProfile:
    """Parse PDF or DOCX resume into a ResumeProfile."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    suffix = p.suffix.lower()
    match suffix:
        case ".pdf":
            raw_text = _extract_text_pdf(p)
        case ".docx":
            raw_text = _extract_text_docx(p)
        case _:
            raise ValueError(f"Unsupported resume format: {suffix}. Use PDF or DOCX.")

    log.info("resume_parsed", path=str(path), chars=len(raw_text))

    skills = _extract_skills(raw_text)
    yoe = _extract_yoe(raw_text)

    log.info("resume_profile", skills=skills, yoe=yoe)

    return ResumeProfile(name=name, raw_text=raw_text, skills=skills, yoe=yoe)
