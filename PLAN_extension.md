# Plan: Job Auto-Fill Browser Extension

## Core Idea
User lands on a job application page → clicks extension icon → extension reads the JD + detects form fields → fills everything intelligently using resume data + Claude API → user reviews and clicks Apply.

**User stays in control. Extension never submits.**

---

## Scope

### What It Does
1. Detects when you're on a job application page
2. Reads the job description from the page
3. Maps form fields to your profile data
4. Uses Claude API to generate tailored answers for open-ended questions
5. Fills all fields, highlights anything it couldn't fill
6. Logs the application (company, role, JD, date, URL) to local storage

### What It Does NOT Do
- Never auto-submits
- Never navigates to job pages on its own
- No scraping of job boards (separate concern — that's radar)

---

## Target ATS Platforms (Priority Order)

### Tier 1 — High Volume Startup ATS (build first)
| ATS | Sites using it | Form type |
|---|---|---|
| Greenhouse | Most YC/funded startups | Standard HTML forms, predictable DOM |
| Lever | Mid-size startups | Similar to Greenhouse |
| Ashby | Newer startups (fast growing) | React-based forms |

### Tier 2 — Direct Job Boards
| Platform | Notes |
|---|---|
| Instahyre | Already familiar, Indian startups |
| Cutshort | Indian startup jobs |
| Arc.dev | Apply directly on site |
| Wellfound (AngelList) | Startup jobs, standard forms |

### Tier 3 — Enterprise ATS (complex, do later)
| ATS | Challenge |
|---|---|
| Workday | iframes + dynamic React, very hard |
| SAP SuccessFactors | Enterprise, multi-step wizard |
| Taleo (Oracle) | Old, inconsistent DOM |
| iCIMS | Complex state machine |

### Skip entirely
- LinkedIn Easy Apply (ToS risk + they detect extensions)
- Naukri / Indeed (Cloudflare + ToS)

---

## Data the Extension Needs

### `resume.json` — your structured profile (one-time setup)
```json
{
  "name": "Venky",
  "email": "venkateshjnv123@gmail.com",
  "phone": "+91-XXXXXXXXXX",
  "location": "Hyderabad, India",
  "linkedin": "https://linkedin.com/in/...",
  "github": "https://github.com/...",
  "resume_url": "https://...",  // hosted PDF link
  "current_company": "Cars24",
  "current_role": "Software Developer",
  "yoe": 3,
  "education": {
    "degree": "B.Tech",
    "institute": "IIT Jodhpur",
    "year": 2022
  },
  "skills": ["Java", "Spring Boot", "Kafka", "Microservices", "AWS", "Python"],
  "salary_expectation": {
    "inr_lpa": "XX",
    "usd_hourly": "XX"
  },
  "notice_period": "X weeks",
  "work_auth": {
    "india": true,
    "us": false,
    "eu": false
  },
  "preferred_roles": ["Backend Engineer", "Software Developer", "Java Developer", "LLM Trainer"]
}
```

---

## Architecture

```
Chrome Extension (Manifest V3)
├── manifest.json
├── background/
│   └── service_worker.js       # Claude API calls, message bus
├── content/
│   ├── detector.js             # Detect ATS type from URL/DOM
│   ├── reader.js               # Extract JD text from page
│   ├── filler.js               # Fill form fields
│   └── sites/
│       ├── greenhouse.js       # Greenhouse-specific selectors
│       ├── lever.js            # Lever-specific selectors
│       ├── ashby.js            # Ashby-specific selectors
│       └── generic.js          # Fallback heuristic filler
├── popup/
│   ├── popup.html              # Extension popup UI
│   └── popup.js
├── data/
│   └── resume.json             # Your profile (never leaves device)
└── prompts/
    └── answer_generator.txt    # Claude prompt template
```

---

## Fill Logic

### Step 1 — Detect ATS
```
URL contains "greenhouse.io"   → use greenhouse.js
URL contains "lever.co"        → use lever.js
URL contains "ashby.com"       → use ashby.js
else                           → generic.js (label-matching heuristic)
```

### Step 2 — Map fields
```
Field label          → resume.json key
"First Name"         → name.split()[0]
"Email"              → email
"Phone"              → phone
"LinkedIn"           → linkedin
"GitHub"             → github
"Years of experience"→ yoe
"Current company"    → current_company
"Notice period"      → notice_period
"Salary expectation" → salary_expectation.*
"Are you authorized?" → work_auth.*
```

### Step 3 — Claude for open-ended fields
```
Fields Claude handles:
- "Why do you want to work here?"
- "Tell us about yourself"
- "What's your biggest achievement?"
- "Cover letter"
- "Describe a challenging project"

Prompt:
  You are Venky, a backend engineer at Cars24 (IIT Jodhpur grad).
  Job: {JD extracted from page}
  Question: {field label + any hint text}
  Write a concise, honest answer in first person. Max 150 words.
```

### Step 4 — Fill + Highlight
- Fill all matched fields silently
- Highlight unfilled fields in yellow
- Show a summary in popup: "12/14 fields filled. 2 need your attention."

---

## Popup UI

```
┌─────────────────────────────┐
│  🤖 JobScout Filler         │
│  Detected: Greenhouse ATS   │
├─────────────────────────────┤
│  Role: Backend Engineer     │
│  Company: Acme Corp         │
├─────────────────────────────┤
│  [Fill All Fields]          │
│                             │
│  ✅ 12 fields filled        │
│  ⚠️  2 fields need review   │
│  → Salary expectation       │
│  → Custom question #2       │
├─────────────────────────────┤
│  [View Application Log]     │
│  [Edit Profile]             │
└─────────────────────────────┘
```

---

## Application Log

Every time you fill + submit, extension logs:
```json
{
  "date": "2026-05-10",
  "company": "Acme Corp",
  "role": "Backend Engineer",
  "url": "https://boards.greenhouse.io/acme/jobs/123",
  "ats": "greenhouse",
  "status": "filled",   // filled / submitted / rejected / interviewing
  "jd_snippet": "We are looking for a Java developer...",
  "claude_answers": { ... }
}
```

Log viewable in extension popup. Can export as CSV.
Later: sync this log with radar digest email.

---

## MVP Scope (v1 — build first)

- [ ] Manifest V3 boilerplate
- [ ] `resume.json` editor in popup settings
- [ ] Greenhouse.js selector map (covers ~40% of startup jobs)
- [ ] Generic label-matching filler (covers another 30%)
- [ ] Claude API call for 3 standard open-ended questions
- [ ] Popup with fill status + field highlights
- [ ] Application log (localStorage)

**Estimate:** ~3–5 days of focused dev work

---

## v2 Scope (after MVP works)

- [ ] Lever + Ashby site files
- [ ] Resume PDF upload auto-detection
- [ ] Instahyre + Cutshort specific fillers
- [ ] "Tailor cover letter" mode — JD-specific rewrite of your pitch
- [ ] Export log → integrate with radar daily digest
- [ ] One-click status update (mark as "got interview", "rejected")

---

## Key Decisions to Make

1. **Claude API key** — stored in extension settings, calls made from background worker. Never exposed to page.
2. **Resume hosted PDF** — where do you host your PDF? (GitHub raw, Google Drive, personal site?)
3. **Open-ended answers** — generate fresh every time, or cache per company?
4. **Salary field** — auto-fill or always flag for manual review? (Negotiation-sensitive)
5. **Start with Greenhouse only?** Or generic filler from day 1?

---

## Risks / Limitations

| Risk | Mitigation |
|---|---|
| ATS changes DOM structure | Site-specific files easy to update, generic fallback always works |
| Claude generates wrong answer | User sees filled text before submitting, can edit |
| Resume data stored in extension | All local, never sent anywhere except Claude API for open-ended Qs |
| Workday / SAP ATS | Out of scope for MVP — these use iframes + shadow DOM |
| Extension detected by ATS | Low risk — extension mimics human typing events |
