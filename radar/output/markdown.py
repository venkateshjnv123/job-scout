"""Markdown digest writer."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from radar.models import ScoredJob

log = structlog.get_logger()

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def write_digest(
    jobs: list[ScoredJob],
    total_scored: int,
    total_passed: int,
    output_dir: str = "./digests",
    run_date: date | None = None,
    gig_jobs: list[ScoredJob] | None = None,
) -> Path:
    """Render and write the markdown digest. Returns the written file path."""
    run_date = run_date or date.today()
    date_str = run_date.strftime("%Y-%m-%d")

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)
    template = env.get_template("digest.md.j2")

    content = template.render(
        date=date_str,
        jobs=jobs,
        gig_jobs=gig_jobs or [],
        total_scored=total_scored,
        total_passed=total_passed,
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.md"
    out_path.write_text(content, encoding="utf-8")

    log.info("digest_written", path=str(out_path), jobs=len(jobs))
    return out_path
