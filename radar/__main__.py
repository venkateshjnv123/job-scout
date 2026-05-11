"""CLI entry point — `python -m radar`."""

from __future__ import annotations

import asyncio
from typing import Optional

import structlog
import typer

from radar.config import load_settings
from radar.dedup import SeenStore
from radar.filters import apply_filters
from radar.models import ScoredJob
from radar.resume.parser import parse_resume
from radar.scoring.rule_based import score_jobs
from radar.sources.findwork import FindworkSource
from radar.sources.himalayas import HimalayasSource
from radar.sources.hn_hiring import HNHiringSource
from radar.sources.instahyre import InstaHyreSource
from radar.sources.jobicy import JobicySource
from radar.sources.reddit import RedditSource
from radar.sources.remoteok import RemoteOKSource
from radar.sources.remotive import RemotiveSource
from radar.sources.upwork import UpworkSource
from radar.sources.weworkremotely import WeWorkRemotelySource
from radar.sources.yc_work import YCWorkSource

app = typer.Typer(help="job-radar: daily backend job digest scored against your resume")
log = structlog.get_logger()


def _print_dry_run(jobs: list[ScoredJob]) -> None:
    """Print top jobs to stdout in a readable format."""
    if not jobs:
        typer.echo("No jobs passed filters + scoring threshold.")
        return

    typer.echo(f"\n{'='*70}")
    typer.echo(f"  JOB RADAR DRY RUN — Top {len(jobs)} matches")
    typer.echo(f"{'='*70}\n")

    for i, job in enumerate(jobs, 1):
        p = job.posting
        skills = ", ".join(job.breakdown.get("matched_skills", []))
        typer.echo(f"#{i}  [{job.score}/100]  {p.title} @ {p.company}")
        typer.echo(f"     Source: {p.source}  |  Location: {p.location}")
        typer.echo(f"     Skills: {skills or 'none matched'}")
        typer.echo(f"     URL: {p.url}")
        if job.llm_verdict:
            typer.echo(f"     Verdict: {job.llm_verdict}")
        typer.echo()


@app.command()
def main(
    config: str = typer.Option("./config.yaml", "--config", "-c", help="Path to config.yaml"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print results to stdout; skip email, file, and dedup"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Run a single source only"),
    no_dedup: bool = typer.Option(False, "--no-dedup", help="Skip dedup check (useful for testing)"),
) -> None:
    """Fetch, filter, score, and deliver your daily job digest."""
    asyncio.run(_run(config=config, dry_run=dry_run, source_filter=source, no_dedup=no_dedup))


async def _run(
    config: str,
    dry_run: bool,
    source_filter: str | None,
    no_dedup: bool = False,
) -> None:
    import httpx

    settings = load_settings(config)
    log.info("radar_start", dry_run=dry_run, source_filter=source_filter)

    # Parse resume
    profile = parse_resume(settings.candidate.resume_path, name=settings.candidate.name)

    # All sources registered here
    reddit_src = RedditSource()
    reddit_src.track = "gig"

    all_sources = {
        "hn_hiring": HNHiringSource(),
        "yc_work": YCWorkSource(),
        "remoteok": RemoteOKSource(),
        "remotive": RemotiveSource(),
        "weworkremotely": WeWorkRemotelySource(),
        "reddit": reddit_src,
        "instahyre": InstaHyreSource(token=settings.instahyre_token, cookies=settings.instahyre_cookies),
        "findwork": FindworkSource(api_key=settings.findwork_api_key),
        "upwork": UpworkSource(),
        "jobicy": JobicySource(),
        "himalayas": HimalayasSource(),
    }

    active = {
        name: src for name, src in all_sources.items()
        if (source_filter is None or name == source_filter)
        and settings.source_enabled(name)
    }

    # Fetch all sources in parallel
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[src.fetch(client) for src in active.values()]
        )

    all_postings = [p for batch in results for p in batch]
    log.info("fetch_complete", total_raw=len(all_postings))

    # Dedup — drop already-seen URLs (skip in dry-run mode)
    if not dry_run and not no_dedup:
        with SeenStore("./seen.db") as store:
            all_postings = store.filter_new(all_postings)

    # Filter
    filtered = apply_filters(
        all_postings,
        locations=settings.candidate.locations,
        must_not_match=settings.candidate.must_not_match,
    )

    # Score
    scored = score_jobs(
        filtered,
        skill_weights=settings.skill_weights,
        yoe_target=settings.candidate.yoe_target,
        min_score=settings.scoring.min_score,
        top_n=settings.scoring.top_n,
    )

    # Optional LLM re-score
    if settings.llm_enabled and scored:
        from radar.scoring.llm import score_with_llm
        scored = await score_with_llm(
            scored, profile, settings.anthropic_api_key,
            settings.skill_weights, settings.candidate.yoe_target
        )
        scored.sort(key=lambda s: s.score, reverse=True)

    log.info("scoring_complete", top_jobs=len(scored))

    # Split by track for two-section output
    fulltime_jobs = [j for j in scored if j.posting.track == "fulltime"]
    gig_jobs = [j for j in scored if j.posting.track == "gig"]

    if dry_run:
        _print_dry_run(scored)
        return

    # Write markdown digest
    if settings.output.markdown.enabled:
        from radar.output.markdown import write_digest
        write_digest(
            fulltime_jobs,
            total_scored=len(all_postings),
            total_passed=len(filtered),
            gig_jobs=gig_jobs,
        )

    # Send email
    if settings.output.email.enabled and settings.smtp_password:
        from radar.output.email import send_digest
        send_digest(
            fulltime_jobs,
            total_scored=len(all_postings),
            total_passed=len(filtered),
            to_addr=settings.output.email.to,
            from_addr=settings.output.email.from_addr,
            smtp_password=settings.smtp_password,
            smtp_host=settings.output.email.smtp_host,
            smtp_port=settings.output.email.smtp_port,
            gig_jobs=gig_jobs,
        )
    elif settings.output.email.enabled and not settings.smtp_password:
        log.warning("email_skipped", reason="SMTP_PASSWORD not set")

    # Mark top-N scored jobs as seen (only after successful output)
    if not no_dedup and scored:
        with SeenStore("./seen.db") as store:
            store.mark_seen([job.posting for job in fulltime_jobs + gig_jobs])


if __name__ == "__main__":
    app()
