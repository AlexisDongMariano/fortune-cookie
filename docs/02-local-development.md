# 02 — Local Development

> Goal: **get the app running on your laptop in under 30 minutes**, then learn how to break and fix it safely.

---

## Prerequisites

Install once. Use whatever package manager you normally use.

| Tool | Version | Verify |
|------|---------|--------|
| Git | any recent | `git --version` |
| Python | 3.11 or 3.12 | `python3 --version` |
| Node.js | 20 LTS | `node --version` |
| (optional) Docker | any recent | `docker --version` |
| (optional) PostgreSQL 15/16 | only needed when you graduate off SQLite | `psql --version` |

**Windows users:** do all of this inside **WSL2 (Ubuntu)**. Native Windows will fight you later on Ansible/Docker. `wsl --install -d Ubuntu` from PowerShell, then open Ubuntu.

**macOS users:** `brew install python@3.12 node@20 git` covers the basics.

---

## 1. Clone + first run (5 min)

```bash
git clone https://github.com/<you>/fortune-cookie.git
cd fortune-cookie
```

> If you haven't created a GitHub repo yet, just `cd` into this folder. You'll push later.

---

## 2. Backend (10 min)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate              # Windows WSL: same. Windows native: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env                   # defaults use SQLite — no DB install needed
python seed_fortunes.py                # creates ./fortune.db + seed rows
uvicorn app.main:app --reload
```

Now open:

- **API docs:** http://localhost:8000/docs — Swagger UI with every endpoint. Click *Try it out*.
- **Health:** http://localhost:8000/healthz — should return `{"status":"ok"}`.

**Sanity check with curl:**

```bash
curl -s http://localhost:8000/api/fortunes/random | python -m json.tool
```

Expected output (example):

```json
{
  "id": 1024,
  "message": "Your next commit will be your best one.",
  "created_at": "2026-04-21T10:30:41.123456",
  "is_favorite": false
}
```

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'app'` | You're running uvicorn from the wrong folder. Be inside `backend/`. |
| `No fortunes seeded. Run …` | You forgot step `python seed_fortunes.py`. |
| Port 8000 in use | `uvicorn app.main:app --reload --port 8001` (then update `vite.config.js` proxy) |

---

## 3. Frontend (10 min)

Open a **second terminal** (leave the backend running).

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Click the cookie. Magic.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| `Failed to fetch /api/...` | Backend isn't running. Check terminal 1. |
| CORS error in browser console | Proxy misconfigured. Confirm `vite.config.js` has `proxy: { "/api": "http://localhost:8000" }` and restart `npm run dev`. |
| Blank page, console: "React refresh runtime" | `rm -rf node_modules .vite && npm install` |

---

## 4. Graduating to PostgreSQL (optional, do this in Week 1 day 7)

SQLite is great for day one. Real jobs use Postgres. Switch early so nothing bites you later.

### Option A — Postgres via Docker (recommended)

```bash
docker run -d --name fortune-pg \
  -e POSTGRES_USER=fortune \
  -e POSTGRES_PASSWORD=fortune \
  -e POSTGRES_DB=fortune \
  -p 5432:5432 \
  postgres:16
```

Edit `backend/.env`:

```
DATABASE_URL=postgresql+psycopg2://fortune:fortune@localhost:5432/fortune
```

Re-seed:

```bash
python seed_fortunes.py
```

### Option B — Native install

`sudo apt install postgresql` (Ubuntu) or `brew install postgresql@16` (macOS). Then:

```bash
sudo -u postgres createuser -P fortune   # set password fortune
sudo -u postgres createdb -O fortune fortune
```

Same `.env` change as above.

### Verifying the switch

```bash
psql -h localhost -U fortune -d fortune -c "SELECT COUNT(*) FROM fortunes;"
```

If you see a count, you're on Postgres.

---

## 5. The daily loop

```bash
# morning
cd fortune-cookie
git pull
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload &
cd ../frontend && npm run dev
```

```bash
# after a change
git status
git add -p                 # -p = review hunks interactively
git commit -m "feat: add favorite toggle button"
git push
```

Commit message convention (Conventional Commits — an actual industry standard, see https://www.conventionalcommits.org):

```
feat:     new user-visible feature
fix:      bug fix
chore:    tidy-ups, renames
docs:     docs only
refactor: no behavior change
test:     test changes
ci:       pipeline changes
```

---

## 6. Local testing (optional for this project, recommended to learn)

CI is out of scope per the roadmap, but one simple `pytest` run will teach you 80% of what you need.

Install once:

```bash
pip install pytest httpx
```

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

Run:

```bash
cd backend
pytest
```

That's enough to show "I know how to write a test" on a resume. Don't let CI perfection block CD progress.

---

## 7. Smoke-test script (keep this around — you'll reuse it on EC2)

Create `scripts/smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8000}"

echo "Healthz..."
curl -fsS "$BASE/healthz"
echo

echo "Random fortune..."
curl -fsS "$BASE/api/fortunes/random" | python -m json.tool

echo "List fortunes..."
curl -fsS "$BASE/api/fortunes?limit=3" | python -m json.tool
```

```bash
chmod +x scripts/smoke.sh
./scripts/smoke.sh                     # local
./scripts/smoke.sh http://<ec2-ip>     # later
```

---

## Definition of Done

- [ ] `uvicorn app.main:app --reload` runs cleanly.
- [ ] `npm run dev` runs cleanly.
- [ ] You've clicked the cookie at least 5 times and favorited 1 message.
- [ ] You've successfully switched to Postgres **or** made a conscious decision to stay on SQLite for now.
- [ ] Your first commit is pushed to GitHub.

Next: [`03-feature-development.md`](03-feature-development.md).
