# 01 — Architecture

> If you remember one thing from this doc: **a web app is three things talking over HTTP — a browser, an API server, and a database.** Everything else is plumbing.

---

## System overview

```
                       ┌──────────────────────────────┐
                       │        Your browser          │
                       │  React SPA (Vite dev server) │
                       │     http://localhost:5173    │
                       └──────────────┬───────────────┘
                                      │  fetch("/api/...")
                                      │  (proxied in dev)
                                      ▼
                       ┌──────────────────────────────┐
                       │      FastAPI backend         │
                       │     http://localhost:8000    │
                       │                              │
                       │  /api/fortunes/random  ──────┼──▶ ┌────────────────┐
                       │  /api/fortunes               │    │ OpenAI API     │
                       │  /api/fortunes/{id}/favorite │    │ (optional;     │
                       │  /healthz                    │ ◀──│ 5s timeout →   │
                       └──────────────┬───────────────┘    │ fall back to   │
                                      │  SQLAlchemy ORM    │ seed on fail)  │
                                      ▼                    └────────────────┘
                       ┌──────────────────────────────┐
                       │   PostgreSQL  (or SQLite)    │
                       │      table: fortunes         │
                       └──────────────────────────────┘
```

In **production** (Week 3+) this becomes:

```
                 ┌──────────────┐
 User's browser ─▶│ Nginx :80    │─▶ static React files (dist/)
                 │ (reverse     │
                 │  proxy)      │─▶ :8000 FastAPI (gunicorn/uvicorn)
                 └──────────────┘          │
                                           ▼
                                    PostgreSQL :5432
                          (all on one EC2 at first; split later)
```

---

## Component map

| Component | Language | Role | Key files |
|-----------|----------|------|-----------|
| **Frontend** | JS (React + Vite) | Renders UI, calls the API | `frontend/src/App.jsx`, `components/*.jsx`, `api.js` |
| **Backend** | Python 3.11 (FastAPI) | Business logic + HTTP API | `backend/app/main.py`, `routers/fortunes.py` |
| **AI service** | Python | Calls OpenAI with fallback-to-seed | `backend/app/services/ai.py` |
| **Database** | PostgreSQL (or SQLite for dev) | Persistence | Managed by SQLAlchemy in `models.py` |
| **Config** | .env files | Secrets + switches | `backend/.env` (gitignored) |

---

## Request flow: clicking the cookie

Trace this on paper. If you can't draw it, read the code until you can.

```
(1) User clicks <div> in FortuneCookie.jsx
    └─ onClick={crack}

(2) crack() sets state "shaking", waits 450ms, then:
    └─ api.getRandomFortune()          ← frontend/src/api.js

(3) fetch("/api/fortunes/random")       ← goes to the Vite dev server

(4) Vite proxy forwards to http://localhost:8000/api/fortunes/random
    (configured in frontend/vite.config.js)

(5) FastAPI router matches  GET /api/fortunes/random
    └─ routers/fortunes.py  get_random_fortune()
         └─ calls services/ai.generate_fortune(db)

(6) generate_fortune():
      if OPENAI_API_KEY is set:
          try  POST https://api.openai.com/v1/chat/completions  (5s timeout)
          on success → return (ai_text, "ai")
          on failure → log warning, fall through
      fallback:
          SELECT * FROM fortunes
          WHERE created_at < '2010-01-01'          -- seed rows only
          ORDER BY RANDOM() LIMIT 1
          return (seed_message, "seed")

(7) New row inserted: a "draw" record
       INSERT INTO fortunes (message, created_at, is_favorite, source)
       VALUES (..., now(), false, 'ai' | 'seed')

(8) JSON returned via Pydantic schema FortuneRead (includes `source`)

(9) React sets state "cracked" + stores `fortune`
    CSS animations run:
      - cookie halves slide/rotate outward
      - paper pops up with the text
      - <SourceBadge source={fortune.source}/> renders ✨ AI or 📜 Default

(10) onNewFortune callback bumps refreshKey in App.jsx
     └─ MessageHistory re-fetches via useEffect
         (each history item also shows its SourceBadge)
```

---

## Data model

**One table**, intentionally small for the MVP:

```
┌──────────────────────────────────────────────────────┐
│ fortunes                                             │
├──────────────┬──────────────┬────────────────────────┤
│ id           │ INTEGER PK   │                        │
│ message      │ VARCHAR(280) │ not null               │
│ created_at   │ DATETIME     │ not null, indexed      │
│ is_favorite  │ BOOLEAN      │ default false          │
│ source       │ VARCHAR(16)  │ 'ai' | 'seed'          │
└──────────────┴──────────────┴────────────────────────┘
```

**Design note — why one table?** For the MVP we overload `fortunes` with two meanings:

1. **Seed rows** (`created_at < 2010-01-01` sentinel) → the pool we fall back to.
2. **Draw rows** (`created_at >= 2010-01-01`, i.e. real user draws) → history.

The `source` column tells you *where a draw came from*:
- `source = "ai"` → OpenAI generated this message live.
- `source = "seed"` → either a seed row, or a draw that fell back to seed because the AI call failed.

In **Stage 03** ("Feature development") you'll be asked to refactor into two proper tables (`fortune_messages` and `fortune_draws`) and learn about migrations. That refactor is a great "before/after" story on your resume.

---

## Directory walkthrough

### Backend (`backend/`)

```
app/
├── __init__.py        (empty — makes `app` a Python package)
├── config.py          settings loaded from .env (pydantic-settings)
├── database.py        engine + SessionLocal + get_db dependency
├── models.py          SQLAlchemy ORM classes  (→ DB tables)
├── schemas.py         Pydantic classes       (→ JSON payloads)
├── main.py            FastAPI app, CORS, router wiring
├── routers/
│   └── fortunes.py    HTTP endpoints
└── services/
    └── ai.py          OpenAI call + automatic fallback to seed

requirements.txt       Python deps (pinned versions)
seed_fortunes.py       one-shot script to insert seed messages
.env.example           template — copy to .env locally
```

**Why these layers?**

| Layer | Responsibility | Rule of thumb |
|-------|----------------|---------------|
| `models.py` | Tables | Only columns + relationships. No logic. |
| `schemas.py` | API contract | What goes in/out over JSON |
| `routers/*.py` | Endpoint wiring | Read request → call service/model → return schema |
| `services/*.py` | External calls & business logic | Network, LLM, integrations — always with a fallback |
| `database.py` | Plumbing | No business logic |
| `config.py` | Environment | One source of truth for settings |

This layering is **standard FastAPI structure** (see the official FastAPI tutorial's "Bigger applications" section). Don't invent your own — companies grep for this shape.

### Frontend (`frontend/`)

```
src/
├── main.jsx           React bootstrap
├── App.jsx            top-level component, holds `refreshKey`
├── index.css          Tailwind layers + cookie-half CSS
├── api.js             thin fetch() wrapper
└── components/
    ├── FortuneCookie.jsx     click → animate → fetch → reveal
    └── MessageHistory.jsx    list of draws + heart toggle

index.html             HTML shell Vite injects into
vite.config.js         dev server + /api proxy
tailwind.config.js     custom colors + keyframes
postcss.config.js      PostCSS plugins for Tailwind
package.json           Node deps
```

---

## Key design decisions (and why)

| Decision | Why |
|----------|-----|
| FastAPI, not Flask | Async-friendly, auto-OpenAPI docs at `/docs`, industry momentum |
| React + Vite, not CRA | CRA is deprecated (as of 2023). Vite is the current default |
| Tailwind, not Bootstrap | Industry default for new projects; no opinionated components to fight |
| SQLAlchemy 2.0 style (`Mapped[]`) | Typed, modern. Old `Column()` style is still OK but 2.0 is the direction |
| Pydantic v2 | FastAPI ≥ 0.100 uses v2 natively |
| SQLite in dev, Postgres in prod | Zero-friction start, real DB when it matters |
| No Alembic yet | Too much ceremony for MVP. Added in Week 2 stretch |
| No auth | Fortune cookies are public by nature. Adds scope creep |

---

## AI integration + graceful fallback (important)

The `/api/fortunes/random` endpoint has **three** possible outcomes, and the code is deliberately structured so the router doesn't know which one happened:

| Scenario | Who handles it | Returned `source` |
|----------|----------------|-------------------|
| `OPENAI_API_KEY` is set and the call succeeds | `services/ai._call_openai()` | `"ai"` |
| Key set, but call throws (timeout, 429, 500, invalid key, no network…) | Caught inside `_call_openai`, logged, returns `None` | `"seed"` |
| Key missing or empty string | `_call_openai` returns `None` immediately | `"seed"` |

The router just calls `generate_fortune(db)` and always gets a `(message, source)` tuple. It never has to deal with exceptions from OpenAI. This is the **graceful-degradation pattern** — a core SRE skill. Memorize this phrase: *"a failing dependency should never take down the whole service."*

The frontend surfaces the result via `<SourceBadge>`:

- ✨ **AI** (indigo gradient) — message came fresh from the LLM.
- 📜 **Default** (stone pill) — message came from the seed collection (either no key or the call failed).

Users always get *a* fortune; they just know where it came from.

**Key code locations:**
- Service: `backend/app/services/ai.py`
- Endpoint wiring: `backend/app/routers/fortunes.py::get_random_fortune`
- Badge component: `frontend/src/components/SourceBadge.jsx`
- Config flags: `backend/app/config.py` (`openai_api_key`, `openai_model`, `openai_timeout_seconds`)

---

## What happens where (cheat sheet)

| Want to change… | Edit this |
|-----------------|-----------|
| the text of a seed fortune | `backend/seed_fortunes.py`, rerun it |
| the AI system prompt / tone | `backend/app/services/ai.py` (`SYSTEM_PROMPT`) |
| the OpenAI model | `OPENAI_MODEL` in `.env` (default `gpt-4o-mini`) |
| the AI call timeout | `OPENAI_TIMEOUT_SECONDS` in `.env` |
| the badge colors / icons | `frontend/src/components/SourceBadge.jsx` |
| the API endpoint shape | `backend/app/schemas.py` + `routers/fortunes.py` |
| the cookie's look | `frontend/src/index.css` + `tailwind.config.js` |
| the animation timing | `tailwind.config.js` keyframes |
| the history sort order | `routers/fortunes.py` `list_fortunes` |

---

## Definition of Done for this chapter

- [ ] You can point to each box in the diagram and name the file that implements it.
- [ ] You can describe what happens in steps (3) through (8) of the request flow **without looking**.
- [ ] You've opened `http://localhost:8000/docs` and clicked every endpoint.

Next: [`02-local-development.md`](02-local-development.md).
