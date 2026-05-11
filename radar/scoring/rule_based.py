"""Rule-based job scorer — returns 0-100 based on skill match, role fit, YoE."""

from __future__ import annotations

import re

from radar.models import JobPosting, ScoredJob

# Skills whose name doesn't literally appear in JDs — map to a better pattern.
_SKILL_PATTERNS: dict[str, str] = {
    "postgres": r"postgres(?:ql)?",
}

_YOE_EXTRACT = re.compile(
    r"(\d+)\s*\+?\s*(?:to\s*(\d+)\s*)?years?",
    re.IGNORECASE,
)

_BACKEND_TITLE = re.compile(
    r"\b(backend|back[\s-]end|sde|sde[\s-]?\d|software\s+engineer|platform\s+engineer"
    r"|software\s+developer|api\s+engineer|server[\s-]side)\b",
    re.IGNORECASE,
)

_ROLE_BODY_KEYWORDS = re.compile(
    r"\b(microservices|distributed|scalable|high[\s-]performance|high[\s-]throughput)\b",
    re.IGNORECASE,
)


def _score_skills(text: str, skill_weights: dict[str, int]) -> tuple[int, list[str]]:
    """Score skill match (0-60). Returns score and list of matched skills."""
    text_lower = text.lower()
    total = 0
    matched: list[str] = []
    for skill, weight in skill_weights.items():
        custom = _SKILL_PATTERNS.get(skill)
        if custom:
            pattern = r"\b" + custom + r"\b"
            if re.search(pattern, text_lower):
                total += weight
                matched.append(skill)
            continue
        pattern = r"\b" + re.escape(skill.replace("_", " ")) + r"\b"
        if re.search(pattern, text_lower):
            total += weight
            matched.append(skill)
        # also match underscore variant
        pattern2 = r"\b" + re.escape(skill) + r"\b"
        if skill != skill.replace("_", " ") and re.search(pattern2, text_lower):
            if skill not in matched:
                total += weight
                matched.append(skill)
    return min(total, 60), matched


def _score_role_fit(title: str, body: str) -> int:
    """Score role fit (0-25)."""
    score = 0
    if _BACKEND_TITLE.search(title):
        score += 15
    if _ROLE_BODY_KEYWORDS.search(body):
        score += 10
    return score


def _extract_yoe_range(text: str) -> tuple[int | None, int | None]:
    """Extract (min_yoe, max_yoe) from JD text. Returns (None, None) if not found."""
    matches = _YOE_EXTRACT.findall(text)
    if not matches:
        return None, None
    # Take the first clear match
    lo_str, hi_str = matches[0]
    lo = int(lo_str)
    hi = int(hi_str) if hi_str else lo
    return lo, hi


def _score_yoe_band(body: str, target_band: list[int]) -> int:
    """Score YoE alignment (0-15)."""
    target_lo, target_hi = target_band[0], target_band[1]
    jd_lo, jd_hi = _extract_yoe_range(body)

    if jd_lo is None:
        # Unspecified — benefit of the doubt
        return 10

    # In band
    if jd_lo >= target_lo and jd_hi <= target_hi + 1:
        return 15
    # Adjacent band (one step off)
    if (jd_lo == target_lo - 1 and jd_hi <= target_hi + 1) or (
        jd_lo == target_lo and jd_hi <= target_hi + 2
    ):
        return 8
    # Outside
    return 0


def score_job(
    posting: JobPosting,
    skill_weights: dict[str, int],
    yoe_target: list[int],
) -> ScoredJob:
    """Score a single job posting. Returns ScoredJob with 0-100 score."""
    text = f"{posting.title} {posting.body}"

    skill_score, matched_skills = _score_skills(text, skill_weights)
    role_score = _score_role_fit(posting.title, posting.body)
    yoe_score = _score_yoe_band(posting.body, yoe_target)

    total = skill_score + role_score + yoe_score

    breakdown = {
        "skill_score": skill_score,
        "role_score": role_score,
        "yoe_score": yoe_score,
        "matched_skills": matched_skills,
    }

    return ScoredJob(posting=posting, score=total, breakdown=breakdown)


def score_jobs(
    postings: list[JobPosting],
    skill_weights: dict[str, int],
    yoe_target: list[int],
    min_score: int = 40,
    top_n: int = 10,
) -> list[ScoredJob]:
    """Score and rank a list of postings. Returns top_n above min_score."""
    scored = [score_job(p, skill_weights, yoe_target) for p in postings]
    filtered = [s for s in scored if s.score >= min_score]
    filtered.sort(key=lambda s: s.score, reverse=True)
    return filtered[:top_n]
