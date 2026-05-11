# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install deps
uv sync

# Run (full pipeline)
uv run python -m radar

# Dry run (no email, no dedup, stdout only)
uv run python -m radar --dry-run

# Single source
uv run python -m radar --dry-run --source hn_hiring

# Tests
uv run pytest
uv run pytest tests/test_scoring_rule_based.py   # single file
uv run pytest --cov=radar --cov-fail-under=70

# Lint + types
uv run ruff check radar tests
uv run mypy radar
```

## Architecture

Pipeline runs in `__main__.py:_run()`:

```
parse_resume → [fetch sources in parallel] → dedup → apply_filters → score_jobs → [llm re-score] → output
```

**Sources** (`radar/sources/`) — each extends `base.Source`, implements `_fetch(client)`. Base class wraps with 10s timeout and fail-open (returns `[]` on any error). All sources fetched concurrently via `asyncio.gather`.

**Filters** (`radar/filters.py`) — drops postings that match `must_not_match` titles/phrases or wrong location. Hard reject before scoring.

**Scoring** (`radar/scoring/`) — two scorers:
- `rule_based.py`: deterministic 0-100 across skill match (0-60) + role fit (0-25) + YoE band (0-15). Jobs below `min_score` (default 40) are dropped; top `top_n` (default 10) returned.
- `llm.py`: optional Claude Haiku re-score, auto-enabled when `ANTHROPIC_API_KEY` env var is set. Falls back to rule-based score on malformed JSON.

**Dedup** (`radar/dedup.py`) — SQLite `seen.db` (gitignored). `SeenStore` used as context manager. Skipped in `--dry-run` and `--no-dedup` modes.

**Config** (`radar/config.py`) — `Settings` is a plain Pydantic model (not `BaseSettings`). `load_settings()` reads `config.yaml` via PyYAML then overlays three secrets from env: `SMTP_PASSWORD`, `ANTHROPIC_API_KEY`, `INSTAHYRE_TOKEN`. Copy `config.example.yaml` → `config.yaml` to get started.

**Output** (`radar/output/`) — `markdown.py` writes `digests/YYYY-MM-DD.md`; `email.py` sends HTML via Gmail SMTP. Both use Jinja2 templates in `radar/output/templates/`.

## Constraints

- No LinkedIn / Naukri / Wellfound / Indeed — Cloudflare-blocked on GH Actions + ToS violations.
- `mypy --strict` must pass; `asyncio` + `httpx` for all HTTP; no `requests`.
- Secrets only via env vars — never in `config.yaml` or code.
- Each source ≤150 LOC.
- GH Actions budget: 2 minutes per run (parallelism is why).
