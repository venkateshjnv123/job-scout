# Claude Code: Build `job-radar`

You are building a Python project from scratch. Read this entire document before writing any code. Ask clarifying questions for anything ambiguous before starting.

## What you are building

An open-source CLI tool called **`job-radar`** that:

1. Parses my resume (PDF or DOCX)
2. Pulls fresh backend job postings from 5-6 free, CI-safe sources
3. Filters to remote / Hyderabad / Bangalore, 2-4 yr band, backend roles
4. Scores each posting against my resume (rule-based default; optional Claude API)
5. Emails me a ranked HTML digest of the top 10
6. Commits a Markdown copy to `digests/YYYY-MM-DD.md`
7. Runs daily at 9 AM IST via GitHub Actions on the free tier

The repo must be forkable by anyone in under 10 minutes — they edit `config.yaml`, add 3 GitHub secrets, and it works.

## Hard constraints (do not violate)

- **No LinkedIn, Naukri, Wellfound, or Indeed scraping.** They are Cloudflare-blocked on GitHub Actions IPs and violate ToS. Skip them entirely. If the user asks, explain why in the README.
- **No auto-apply functionality.** This is a discovery + ranking tool, not an application bot.
- **Python 3.11+ only.** Use modern syntax (`match`, `|` unions, `TypedDict`, etc.).
- **Zero paid infra.** GitHub Actions free tier + Gmail SMTP only.
- **GitHub Actions runtime budget: 2 minutes.** Parallelize source fetches with `asyncio` / `httpx.AsyncClient`.

## Repo structure (build exactly this)

```
job-radar/
├── README.md                    # see "README requirements" below
├── LICENSE                      # MIT
├── pyproject.toml               # uv / hatch managed; pin all deps
├── .gitignore                   # incl. config.yaml, *.pdf, *.docx, seen.db
├── config.example.yaml          # documented template
├── resume.example.txt           # placeholder; user replaces with real PDF/DOCX
├── radar/
│   ├── __init__.py
│   ├── __main__.py              # `python -m radar` entry point
│   ├── config.py                # pydantic Settings, loads config.yaml + env
│   ├── models.py                # JobPosting, ResumeProfile, ScoredJob (pydantic)
│   ├── resume/
│   │   ├── __init__.py
│   │   ├── parser.py            # pdfplumber + python-docx
│   │   └── normalizer.py        # skill canonicalization (java=Java, sb=Spring Boot)
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py              # abstract Source (async fetch, timeout=10s, fail-open)
│   │   ├── hn_hiring.py         # Algolia HN Search API
│   │   ├── yc_work.py           # workatastartup.com public JSON
│   │   ├── remoteok.py          # remoteok.com/api
│   │   ├── remotive.py          # remotive.com/api/remote-jobs
│   │   ├── weworkremotely.py    # RSS
│   │   └── instahyre.py         # API, requires auth token (graceful skip if absent)
│   ├── filters.py               # location / YoE / title filters
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── rule_based.py        # weighted skill + role + YoE; returns 0-100
│   │   └── llm.py               # optional, uses ANTHROPIC_API_KEY if set
│   ├── dedup.py                 # SQLite-backed seen-URL store
│   └── output/
│       ├── __init__.py
│       ├── email.py             # SMTP, Jinja2 HTML template
│       ├── markdown.py          # writes digests/YYYY-MM-DD.md
│       └── templates/
│           ├── digest.html.j2
│           └── digest.md.j2
├── tests/
│   ├── conftest.py
│   ├── test_resume_parser.py
│   ├── test_filters.py
│   ├── test_scoring_rule_based.py
│   ├── test_dedup.py
│   └── fixtures/                # sample JDs, sample resume
├── .github/
│   └── workflows/
│       ├── daily.yml            # cron 0 3 * * * (3 UTC = 8:30 IST, run a bit early)
│       └── ci.yml               # tests + mypy + ruff on PR
└── digests/
    └── .gitkeep
```

## Tech stack (use these specifically)

- **HTTP:** `httpx` async client, not `requests`
- **HTML/RSS parse:** `selectolax` (fast) or `beautifulsoup4` + `feedparser`
- **Resume parse:** `pdfplumber` for PDF, `python-docx` for DOCX
- **Config:** `pydantic-settings` v2
- **Templates:** `jinja2`
- **CLI:** `typer` (so `python -m radar --dry-run`, `--source hn_hiring`, etc. work)
- **Logging:** `structlog` with JSON output (better for CI logs)
- **Tests:** `pytest`, `pytest-asyncio`, `respx` for HTTP mocking
- **Lint/type:** `ruff` + `mypy --strict`
- **Package mgmt:** `uv` (faster than pip, deterministic)

## Scoring algorithm (rule-based default)

Each job gets 0-100:

- **Tier 1 — Hard filters (binary):** drop if location doesn't match, title contains staff/principal/lead/director/sr-staff, or JD says "5+ years" / "7+ years" / "10+ years"
- **Tier 2 — Skill match (0-60):**
  - From `config.yaml`: `skill_weights: {java: 10, spring: 10, kafka: 7, postgres: 5, redis: 5, microservices: 8, rabbitmq: 5, aws: 5, system_design: 5}`
  - Sum weights for skills appearing (case-insensitive, word-boundary regex) in JD title + body. Cap at 60.
- **Tier 3 — Role fit (0-25):**
  - Title contains backend/SDE/software engineer/platform: +15
  - JD body contains microservices/distributed/scalable: +10
- **Tier 4 — YoE band (0-15):**
  - Regex `(\d+)\s*\+?\s*(?:to\s*\d+\s*)?years?` against JD
  - In configured target band [2, 4]: +15; adjacent (1-3 or 4-6): +8; outside: 0; unspecified: +10 (give benefit of the doubt)

Below 40 → don't include in digest. Show top 10 by score.

## LLM scoring (optional, behind feature flag)

If `ANTHROPIC_API_KEY` is set in env:

- Use `claude-haiku-4-5-20251001` (cheap, fast)
- One call per job that passed hard filters, max 30 jobs/run
- Prompt template:
  ```
  Score this job for a candidate.

  CANDIDATE PROFILE:
  {resume_summary}

  JOB:
  Title: {title}
  Company: {company}
  Description: {description_first_2000_chars}

  Return ONLY valid JSON:
  {
    "score": <0-100>,
    "verdict": "<one line: strong fit / decent / skip — and why>",
    "matched_skills": [<top 3-5>],
    "gaps": [<top 2-3>],
    "resume_emphasis": "<which 1-2 resume bullets to lead with>",
    "pitch": "<2-line cold opener>"
  }
  ```
- Set `max_tokens=600`. Parse defensively — if JSON malformed, fall back to rule-based score.
- Log estimated cost per run.

## Configuration (`config.example.yaml`)

```yaml
candidate:
  resume_path: ./resume.pdf            # PDF or DOCX
  name: Your Name
  yoe_target: [2, 4]
  locations: [remote, hyderabad, bangalore]
  must_not_match: [senior, staff, principal, lead, director, "5+ years", "7+ years"]

skill_weights:
  java: 10
  spring: 10
  spring_boot: 10
  kafka: 7
  rabbitmq: 5
  postgres: 5
  redis: 5
  microservices: 8
  aws: 5
  system_design: 5

sources:
  hn_hiring: { enabled: true }
  yc_work: { enabled: true }
  remoteok: { enabled: true }
  remotive: { enabled: true }
  weworkremotely: { enabled: true }
  instahyre: { enabled: false }        # set true and add INSTAHYRE_TOKEN secret

scoring:
  use_llm: false                        # auto-true if ANTHROPIC_API_KEY set
  min_score: 40
  top_n: 10

output:
  email:
    enabled: true
    to: you@example.com
    from: you@gmail.com                 # Gmail app password via SMTP_PASSWORD secret
    smtp_host: smtp.gmail.com
    smtp_port: 587
  markdown:
    enabled: true
    commit_to_repo: true                # GH Actions auto-commits
```

## GitHub Actions workflow

`daily.yml`:
- Cron: `0 3 * * *` (3:00 UTC = 8:30 AM IST — run before 9 so the email lands at 9)
- Steps: checkout → setup-uv → `uv sync` → `python -m radar` → commit `digests/*.md` if new file
- Secrets needed: `SMTP_PASSWORD`, optional `ANTHROPIC_API_KEY`, optional `INSTAHYRE_TOKEN`
- Use `actions/checkout@v4` with `persist-credentials: true` so the auto-commit step works
- Use a permissions block: `contents: write`

`ci.yml`:
- Runs on PR: `uv run ruff check`, `uv run mypy radar`, `uv run pytest --cov=radar --cov-fail-under=70`

## README requirements

The README must enable a 10-minute fork. Sections:

1. What it does (1 paragraph + 1 sample digest screenshot — generate a placeholder)
2. **Quickstart (5 commands max):**
   ```
   gh repo fork venkateshjnv123/job-radar --clone
   cd job-radar
   cp config.example.yaml config.yaml          # edit it
   gh secret set SMTP_PASSWORD                  # paste Gmail app password
   git push                                     # GitHub Actions handles the rest
   ```
3. How scoring works (link to `scoring/rule_based.py`, explain weights)
4. Why no LinkedIn / Naukri (Cloudflare + ToS, in 3 sentences)
5. Adding a new source (point to `sources/base.py`)
6. Cost: $0 (table showing free-tier usage)
7. Roadmap (parking lot from PRD)
8. License (MIT)

## Build order — execute in 3 phases. Stop and report after each.

### Phase 1 — Walking skeleton (target: works end-to-end on one source)

1. Init repo: `pyproject.toml`, `.gitignore`, `LICENSE`, basic `README.md` stub
2. Models: `JobPosting`, `ResumeProfile`, `ScoredJob` (pydantic)
3. Resume parser (PDF + DOCX), with tests using a sample resume in `tests/fixtures/`
4. ONE source: `hn_hiring.py` (Algolia API — easiest, cleanest JSON)
5. Filters module + tests
6. Rule-based scorer + tests (≥70% coverage on this file)
7. Markdown output + tests
8. CLI entry point: `python -m radar --dry-run` prints top 10 to stdout
9. **Stop. Show me a sample run output and confirm before Phase 2.**

### Phase 2 — Full source coverage + email

1. Add: `yc_work`, `remoteok`, `remotive`, `weworkremotely`, `instahyre`
2. Async parallel fetch with `httpx.AsyncClient`, 10s timeout per source, fail-open
3. SQLite dedup (`seen.db`, gitignored)
4. HTML email output via SMTP with Jinja2 template
5. End-to-end integration test using `respx` to mock all sources
6. **Stop. Run a real digest against my live email. Confirm before Phase 3.**

### Phase 3 — CI/CD + LLM scoring + polish

1. `.github/workflows/daily.yml` and `ci.yml`
2. Auto-commit logic for `digests/*.md`
3. Optional Claude scoring (`scoring/llm.py`) — feature-flagged on `ANTHROPIC_API_KEY` presence
4. Full README with quickstart, screenshots, roadmap
5. `mypy --strict` clean, `ruff` clean, coverage ≥70%
6. Sample digest committed to `digests/` so the repo isn't empty on first clone
7. **Stop. Show final tree, test output, and a live GitHub Actions run.**

## Coding standards

- Type hints everywhere; `mypy --strict` must pass
- No `print()` in library code — use `structlog`
- Each public function gets a docstring with one-line summary + Args/Returns
- No bare `except:` — always specific exceptions
- Network calls always have timeouts
- Secrets only via env vars, never in code or config.yaml
- Each source ≤150 LOC; if longer, refactor

## Things to ask me before starting

1. Do I want `uv` or stick with `pip + venv`? (Recommend uv.)
2. What's my GitHub username for the README clone command?
3. Should the Markdown digest template include the LLM `pitch` field, or keep it email-only to avoid leaking prompts in the public repo?
4. For the sample resume in `tests/fixtures/`, should you generate a fake one or do I provide a sanitized version of mine?

Once these are answered, start Phase 1. Do not skip ahead.
