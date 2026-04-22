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
                       │  /api/fortunes/random        │
                       │  /api/fortunes               │
                       │  /api/fortunes/{id}/favorite │
                       │  /healthz                    │
                       └──────────────┬───────────────┘
                                      │  SQLAlchemy ORM
                                      ▼
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

(6) SQLAlchemy query:
       SELECT * FROM fortunes WHERE id <= 1000 ORDER BY RANDOM() LIMIT 1

(7) New row inserted: a "draw" record with now() timestamp
       INSERT INTO fortunes (message, created_at, is_favorite) ...

(8) JSON returned via Pydantic schema FortuneRead

(9) React sets state "cracked" + stores `fortune`
    CSS animations run:
      - cookie halves slide/rotate outward
      - paper pops up with the text

(10) onNewFortune callback bumps refreshKey in App.jsx
     └─ MessageHistory re-fetches via useEffect
```

---

## Data model

**One table**, intentionally small for the MVP:

```
┌─────────────────────────────────────────────────┐
│ fortunes                                        │
├──────────────┬──────────────┬───────────────────┤
│ id           │ INTEGER PK   │                   │
│ message      │ VARCHAR(280) │ not null          │
│ created_at   │ DATETIME     │ not null, indexed │
│ is_favorite  │ BOOLEAN      │ default false     │
└──────────────┴──────────────┴───────────────────┘
```

**Design note — why one table?** For the MVP we overload `fortunes` with two meanings:

1. **Seed rows** (ids ≤ 1000, `created_at = 2000-01-01`) → the pool we pick from.
2. **Draw rows** (ids > 1000, `created_at = now()`) → the user's history.

This keeps the starter code simple. In **Stage 03** ("Feature development") you'll be asked to refactor it into two proper tables (`fortune_messages` and `fortune_draws`) and learn about migrations. That refactor is a great "before/after" story on your resume.

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
└── routers/
    └── fortunes.py    HTTP endpoints

requirements.txt       Python deps (pinned versions)
seed_fortunes.py       one-shot script to insert seed messages
.env.example           template — copy to .env locally
```

**Why these layers?**

| Layer | Responsibility | Rule of thumb |
|-------|----------------|---------------|
| `models.py` | Tables | Only columns + relationships. No logic. |
| `schemas.py` | API contract | What goes in/out over JSON |
| `routers/*.py` | Endpoint wiring | Read request → call model → return schema |
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

## What happens where (cheat sheet)

| Want to change… | Edit this |
|-----------------|-----------|
| the text of a fortune | `backend/seed_fortunes.py`, rerun it |
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
