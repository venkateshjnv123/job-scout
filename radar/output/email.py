"""HTML email output via Gmail SMTP — Phase 2 stub, wired in Phase 2."""

from __future__ import annotations

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from radar.models import ScoredJob

log = structlog.get_logger()

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def send_digest(
    jobs: list[ScoredJob],
    total_scored: int,
    total_passed: int,
    to_addr: str,
    from_addr: str,
    smtp_password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    run_date: date | None = None,
    gig_jobs: list[ScoredJob] | None = None,
) -> None:
    """Send HTML digest email via Gmail SMTP."""
    run_date = run_date or date.today()
    date_str = run_date.strftime("%Y-%m-%d")
    gig_jobs = gig_jobs or []

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("digest.html.j2")
    html_body = template.render(
        date=date_str,
        jobs=jobs,
        gig_jobs=gig_jobs,
        total_scored=total_scored,
        total_passed=total_passed,
    )

    msg = MIMEMultipart("alternative")
    gig_part = f" · {len(gig_jobs)} gigs" if gig_jobs else ""
    msg["Subject"] = f"Job Radar — {len(jobs)} jobs{gig_part} · {date_str}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(from_addr, smtp_password)
        server.sendmail(from_addr, to_addr, msg.as_string())

    log.info("email_sent", to=to_addr, jobs=len(jobs))
