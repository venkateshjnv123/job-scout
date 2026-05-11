# Plan: Reddit + Remote Contract Platforms + Auto-Apply Bot

## Context
Current sources: HN Hiring, RemoteOK, Remotive, WeWorkRemotely, Instahyre, YC Work.
Profile: Software developer, IIT Jodhpur, Java/Spring/Kafka/Microservices stack.

---

## Part 1: Add Reddit Job Subreddits as Sources

### Target Subreddits (from screenshot)
| Subreddit | Focus |
|---|---|
| r/remotework | General remote jobs |
| r/WorkOnline | Online/remote work |
| r/freelance | Freelance gigs |
| r/forhire | Freelance + contract |
| r/hiring | Direct hiring posts |
| r/jobbit | Tech job board |
| r/remotejobs | Remote only |
| r/digitalnomad | Remote/nomad jobs |
| r/Upwork | Upwork-style gigs |
| r/freelanceWriters | Skip — not relevant |

### Relevant Target Roles (filter in scoring)
- LLM Trainer / AI Trainer / RLHF
- Software Developer / Backend Engineer
- App Developer (Android/iOS/Flutter)
- Java Developer / Spring Boot Engineer

### API Approach
- Use Reddit JSON API (no auth needed): `https://www.reddit.com/r/{sub}/new.json?limit=100`
- Filter posts with `[Hiring]` or `[For Hire]` flair or title keywords
- Map to `JobPosting` model — title, company (OP username as fallback), url, body

### Implementation Plan

**File:** `radar/sources/reddit_jobs.py`

```
class RedditJobsSource(Source):
    name = "reddit_jobs"
    SUBREDDITS = ["forhire", "hiring", "jobbit", "remotejobs", "WorkOnline"]
    
    _fetch() → for each subreddit, GET /new.json
             → filter posts where flair contains [Hiring] or title contains hiring keywords
             → parse into JobPosting
             → return combined list (deduplicated by URL)
```

**Config addition** (`config.yaml`):
```yaml
sources:
  reddit_jobs:
    enabled: true
```

**Scoring keywords to add** (`config.yaml` → `skill_weights`):
```yaml
skill_weights:
  llm: 10
  rlhf: 10
  ai_trainer: 10
  python: 8
  android: 6
  flutter: 6
  java: 10   # already exists
```

**Filter roles** (`config.yaml` → `candidate.must_not_match`): keep as-is, Reddit posts are looser.

### Effort
- ~1–2 hours, ~120 LOC (fits ≤150 constraint)
- No auth token needed (Reddit public JSON API)
- Rate limit: 1 req/sec → fetch subreddits sequentially inside the source

---

## Part 2: Remote Contract Platforms to Add as Sources

Grouped by category. Each needs its own fetch strategy.

### 🤖 AI / LLM Trainer Platforms (High Priority for your profile)
| Platform | API/Scrape Approach | Notes |
|---|---|---|
| [Mercor](https://mercor.com) | No public API — check job board page | $95/hr avg, works with OpenAI/Anthropic |
| [Outlier.ai](https://outlier.ai) | No public API — scrape listings page | Scale AI subsidiary, pays $15–$50/hr |
| [Scale AI](https://scale.com/jobs) | No public API — scrape job board | Top AI data platform |
| [Surge AI](https://surgehq.ai) | No public API | RLHF specialist, pays up to $1000/hr for experts |
| [Remotasks](https://remotasks.com) | No public API | Scale AI brand, annotation + AI training tasks |
| [DataAnnotation.tech](https://dataannotation.tech) | Scrape job board | Good for LLM code evaluation gigs |
| [Appen](https://appen.com) | Has job listings page | Long-standing annotation platform |

### 🏆 Vetted Developer Networks (Apply once, get matched)
| Platform | API/Scrape Approach | Notes |
|---|---|---|
| [Turing](https://turing.com) | No public API — apply as developer | AI-matched, full-time remote |
| [Toptal](https://toptal.com) | No public API — developer application | Top 3% filter, premium rates |
| [Arc.dev](https://arc.dev) | Has job board JSON-ish listings | Top 2%, fast matching |
| [Andela](https://andela.com) | Has job listings page | Global, coding challenge vetting |
| [Lemon.io](https://lemon.io) | No public API | Startup-focused, 90-min assessment |
| [Braintrust](https://usebraintrust.com) | Has public job board (GraphQL API) | 0% fee to talent, decentralized |
| [Pesto.tech](https://pesto.tech) | No public API | India-focused, US remote roles |

### 💼 Freelance Marketplaces (Open job boards — scrapeable)
| Platform | API/Scrape Approach | Notes |
|---|---|---|
| [Upwork](https://upwork.com) | Has RSS feeds per category | Largest marketplace, high competition |
| [Freelancer.com](https://freelancer.com) | Has public API | 18M+ freelancers |
| [Guru.com](https://guru.com) | Has job board | Mid-tier marketplace |
| [Fiverr Pro](https://fiverr.com/pro) | No scrape-friendly API | Gig-based, not ideal for dev contracts |
| [PeoplePerHour](https://peopleperhour.com) | Has job board | UK-focused remote |
| [Contra](https://contra.com) | Has job board | 0% commission to freelancers |

### 🌍 Remote Job Boards (Already have some — expand these)
| Platform | API/Scrape Approach | Notes |
|---|---|---|
| [Remotive](https://remotive.com) | ✅ JSON API exists | Already in radar |
| [WeWorkRemotely](https://weworkremotely.com) | ✅ RSS feed | Already in radar |
| [RemoteOK](https://remoteok.com) | ✅ JSON API | Already in radar |
| [Remote.co](https://remote.co) | RSS feed | Curated remote-only |
| [Jobspresso](https://jobspresso.co) | Scrapeable | Curated, smaller |
| [FlexJobs](https://flexjobs.com) | Requires paid account | Skip |
| [Remote.io](https://remote.io) | Has JSON feed | Aggregator |
| [Himalayas](https://himalayas.app) | Has public API / JSON | Fast-growing remote board |
| [Nodesk](https://nodesk.co/remote-jobs/) | Scrapeable | Curated list |

### 🇮🇳 India-Specific Remote/Contract (Relevant for you)
| Platform | API/Scrape Approach | Notes |
|---|---|---|
| [Instahyre](https://instahyre.com) | ✅ Token-based API | Already in radar |
| [Cutshort](https://cutshort.io) | Has job board | Startup-focused India |
| [Hasjob](https://hasjob.co) | Has JSON API | India remote/startup jobs |
| [Internshala](https://internshala.com) | Scrapeable | Contract/part-time gigs too |
| [Freelancer India](https://freelancer.in) | Has API | India-specific contracts |

---

### Fetch Strategy by Type

```
Type A — Public JSON/RSS API     → build as Source (easy, like existing ones)
Type B — Scrapeable HTML         → httpx + BeautifulSoup, still within ~150 LOC
Type C — No API, apply manually  → NOT a source; add to a "manual platforms" list in digest
```

**Recommended new sources to build (Type A/B):**
1. `reddit_jobs.py` — covers 5+ subreddits, JSON API, no auth
2. `arc_dev.py` — Arc has JSON-ish listings, filterable by role
3. `braintrust.py` — GraphQL job board, 0% fee platform
4. `himalayas.py` — public API, fast-growing
5. `hasjob.py` — India remote, JSON API

**Manual platforms (scraping too risky / no API):**
- Turing, Toptal, Mercor, Lemon.io, Andela — apply once manually, they match you

---

## Part 3: Auto-Apply Bot (Browser Extension / Scraper)

### What You Want
> "A bot that can go into any job page and apply for me — like an extension"

### Two Approaches

#### Option A: Browser Extension (Recommended for safety + flexibility)
- Chrome/Firefox extension that injects a "Apply with AI" button on job pages
- On click: reads the job description from the page, autofills forms using your resume data
- Works on: LinkedIn, Naukri, Instahyre, Indeed, any ATS (Greenhouse, Lever, Workday)
- **Stack:** Manifest V3, content scripts, popup UI, background service worker
- **AI fill:** Calls Claude API (your key) to generate tailored answers to custom questions

**Architecture:**
```
Extension popup → user clicks "Apply"
  → content script reads job JD from DOM
  → sends to background worker
  → background calls Claude API with JD + resume context
  → fills form fields intelligently
  → flags fields it can't fill (custom essay questions)
```

**Pros:**
- Works on any site without scraping
- You stay in control (review before submit)
- No ToS violations (you're clicking yourself)

**Cons:**
- Need to build per-site DOM selectors for form filling
- Workday/SAP forms are notoriously hard to automate

#### Option B: Headless Scraper Bot (Playwright/Puppeteer)
- Runs server-side, navigates to job pages, fills forms
- Can be scheduled via GH Actions or cron
- **Stack:** Playwright + Python (fits existing radar stack)

**Pros:**
- Fully automated, no manual trigger
- Integrates with existing radar pipeline

**Cons:**
- High ToS violation risk (LinkedIn, Naukri, Indeed all ban bots)
- CAPTCHAs, Cloudflare blocks (already noted in CLAUDE.md)
- Easy to get your IP/account banned
- Risky for job applications (wrong application = blacklisted)

### Recommendation
**Build Option A (Extension) first.** Safer, more reliable, you stay in control.

#### Extension MVP Scope
1. **Phase 1:** "One-click fill" — reads JD, pre-fills name/email/phone/resume upload
2. **Phase 2:** Claude-powered answer generation for "Why do you want this role?" fields
3. **Phase 3:** Track applications in a local JSON/SQLite log, sync with radar digest

#### Possible Files
```
jobscout-extension/
  manifest.json
  background.js          # Claude API calls
  content/
    detector.js          # detect job application forms
    filler.js            # fill form fields
  popup/
    popup.html
    popup.js
  data/
    resume.json          # structured resume (parsed from your PDF once)
  prompts/
    cover_letter.txt     # template for Claude
```

---

## Decision Points (Discuss Before Starting)

1. **Reddit source** — Which subreddits to prioritize? All 10 or just `forhire`, `hiring`, `remotejobs`?
2. **Role filters** — Should LLM Trainer / AI Trainer jobs be scored high even if pay is lower? (Scale work)
3. **Auto-apply scope** — Do you want a Chrome extension or are you okay triggering a script manually?
4. **Form fill safety** — Should bot submit directly, or just fill and wait for your review + click?
5. **Which job sites first?** — Instahyre? LinkedIn (risky)? Greenhouse-based startups?

---

## Suggested Next Steps

- [ ] Build `reddit_jobs.py` source (quick win, no auth needed)
- [ ] Add LLM/AI trainer role keywords to scoring config
- [ ] Scaffold Chrome extension with Manifest V3 boilerplate
- [ ] Parse resume PDF → `resume.json` (one-time, used by extension)
- [ ] Build form detector for Greenhouse/Lever ATS (most startups use these)
