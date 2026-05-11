# JobScout — Task Backlog

## Active Issues

### 1. Fix `postgres` skill matching `PostgreSQL`  
**Priority: High**

`config.yaml` uses key `postgres` (weight 5). Job postings always say "PostgreSQL", never "postgres".
Scorer does case-insensitive match but needs the exact word — "PostgreSQL" doesn't contain "postgres" as a word boundary.

**Fix:** In `rule_based.py::_score_skills`, add alias expansion so `postgres` also matches `postgresql`.
Or rename the key in config to `postgresql` and update docs.

---

### 2. Add India-focused job sources  
**Priority: Critical — root cause of 0 jobs**

All current sources are Western-remote-biased:

| Source | Count | Stack bias |
|--------|-------|------------|
| hn_hiring | 200 | Python, Go, TypeScript |
| remoteok | 97 | Python, Go, JS |
| remotive | 20 | Mixed, mostly US |
| weworkremotely | 12 | US companies |
| reddit (r/forhire) | 100 | Freelance, US-skewed |
| yc_work | 0 (error) | YC startups, mixed |

Java + Spring Boot is the dominant stack in Hyderabad/Bangalore startups — not on these boards.

**Options to investigate:**
- Enable **Instahyre** (already wired, needs `INSTAHYRE_TOKEN` secret)
- **Cutshort** — has a public API, India-focused tech jobs
- **Naukri RSS** — technically blocked per CLAUDE.md constraints (ToS)
- Add `docker`, `kubernetes`, `node`, `typescript` to `skill_weights` to catch more JS/TS jobs as fallback

---

### 3. Fix yc_work source 406 error  
**Priority: Medium**

`yc_work` returns HTTP 406 (Not Acceptable). Endpoint rejects the request headers.

**Fix:** Add `Accept: application/json` and/or a realistic `User-Agent` to the request in `radar/sources/yc_work.py`.

---

### 4. Add `reddit` to config.yaml explicitly  
**Priority: Low**

`source_enabled()` returns `True` for any source not in `config.yaml`. Reddit runs silently.

**Fix:** Add `reddit: { enabled: true }` (or `false`) to `config.yaml` sources block so it's visible.
Also evaluate: r/forhire posts are mostly US freelance gigs — low value for Hyderabad/Bangalore search.

---

### 5. Set up 8AM IST daily cron  
**Priority: Medium**

Run `uv run python -m radar` every morning at 8AM IST = **02:30 UTC**.

**Plan:** Add `.github/workflows/daily.yml`:
```yaml
on:
  schedule:
    - cron: '30 2 * * *'   # 8:00 AM IST
  workflow_dispatch:        # manual trigger
```

**GitHub Actions secrets needed:**
- `SMTP_PASSWORD` — Gmail app password
- `ANTHROPIC_API_KEY` — optional, enables LLM re-scoring
- `INSTAHYRE_TOKEN` — optional, enables Instahyre source

**Note:** Repo must be public OR on a paid plan for Actions minutes. `seen.db` won't persist between runs unless committed or stored in Actions cache — decide approach first.

---

## Done

- [x] **Fix `postgres` matching `PostgreSQL`** — added `_SKILL_PATTERNS` alias in `rule_based.py`: `postgres → postgres(?:ql)?`
- [x] **Fix yc_work 406** — replaced bot User-Agent with browser-like headers + `Accept: text/html`
- [x] **Add `reddit` to config.yaml** — set `enabled: false` (r/forhire is US freelance, low value)
- [x] **Instahyre source rewritten** — switched to `/api/v1/job_search` endpoint, cookie auth via `INSTAHYRE_COOKIES` env var. Fetches 5 pages (175 jobs), uses `keywords` array as body. Produces real results (10 Java backend jobs @ Adobe, Lufthansa, Roku etc).
- [x] **Findwork source added** — `radar/sources/findwork.py`, token auth via `FINDWORK_API_KEY`. Queries `java spring backend / java microservices / java kafka backend`. Full JD text + keywords in body. Works end-to-end.
