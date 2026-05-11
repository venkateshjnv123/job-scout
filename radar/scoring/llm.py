"""Optional LLM scoring via Claude API — activated by ANTHROPIC_API_KEY."""

from __future__ import annotations

import json
import re

import structlog

from radar.models import ResumeProfile, ScoredJob
from radar.scoring.rule_based import score_job

log = structlog.get_logger()

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 600
_MAX_JOBS = 30

_PROMPT_TEMPLATE = """\
Score this job for a candidate.

CANDIDATE PROFILE:
{resume_summary}

JOB:
Title: {title}
Company: {company}
Description: {description}

Return ONLY valid JSON:
{{
  "score": <0-100>,
  "verdict": "<one line: strong fit / decent / skip — and why>",
  "matched_skills": [<top 3-5>],
  "gaps": [<top 2-3>],
  "resume_emphasis": "<which 1-2 resume bullets to lead with>",
  "pitch": "<2-line cold opener>"
}}"""


def _build_resume_summary(profile: ResumeProfile) -> str:
    skills_str = ", ".join(profile.skills[:20]) if profile.skills else "Not specified"
    yoe_str = f"{profile.yoe} years" if profile.yoe else "Not specified"
    return f"Name: {profile.name}\nYears of experience: {yoe_str}\nSkills: {skills_str}"


async def score_with_llm(
    jobs: list[ScoredJob],
    profile: ResumeProfile,
    api_key: str,
    skill_weights: dict[str, int],
    yoe_target: list[int],
) -> list[ScoredJob]:
    """Re-score jobs using Claude. Falls back to rule-based on parse failure."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    resume_summary = _build_resume_summary(profile)
    results: list[ScoredJob] = []
    total_cost_estimate = 0.0

    for job in jobs[:_MAX_JOBS]:
        description = job.posting.body[:2000]
        prompt = _PROMPT_TEMPLATE.format(
            resume_summary=resume_summary,
            title=job.posting.title,
            company=job.posting.company,
            description=description,
        )
        try:
            message = await client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
            data = json.loads(raw)

            llm_score = max(0, min(100, int(data.get("score", job.score))))
            # Rough cost estimate: ~400 input + 200 output tokens at Haiku pricing
            total_cost_estimate += (400 * 0.00000025) + (200 * 0.00000125)

            results.append(
                ScoredJob(
                    posting=job.posting,
                    score=llm_score,
                    breakdown=job.breakdown,
                    llm_verdict=data.get("verdict"),
                    llm_matched_skills=data.get("matched_skills", []),
                    llm_gaps=data.get("gaps", []),
                    llm_pitch=data.get("pitch"),
                    llm_resume_emphasis=data.get("resume_emphasis"),
                )
            )
        except (json.JSONDecodeError, KeyError, IndexError, Exception) as e:
            log.warning("llm_score_failed", job_id=job.posting.id, error=str(e))
            results.append(job)

    log.info("llm_scoring_complete", jobs=len(results), estimated_cost_usd=round(total_cost_estimate, 4))
    return results
