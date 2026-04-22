# Fortune Cookie Generator — DevOps/SRE Portfolio Project

A full-stack web app you build end-to-end to learn **Programming, CI/CD, Docker, Ansible, Terraform, AWS, Prometheus/Grafana, and Kubernetes** in one cohesive portfolio piece.

**Stack:** FastAPI · PostgreSQL · React + Vite + Tailwind · OpenAI *(optional, with graceful fallback)* · Docker · GitHub Actions · Ansible · Terraform · AWS EC2 *(or Azure VM — see appendix)* · Prometheus · Grafana · (optional) Kubernetes.

---

## Why this project?

Employers want to see that you can **ship something real**. This project is deliberately small enough to finish in 4–6 weeks but rich enough that you'll touch every layer of a modern production system: code, database, containers, cloud infra, configuration management, CI/CD, and observability.

Every chapter is self-contained — you (or an AI assistant) can pick up at any point by opening the right doc.

---

## How to use these docs

1. **Start with [`docs/00-roadmap.md`](docs/00-roadmap.md)** — the week-by-week plan with milestones and checkpoints.
2. Work through the numbered guides in order. Each ends with a **Definition of Done** checklist.
3. If you get stuck, the [`docs/reference/`](docs/reference/) folder has git/bash cheatsheets and troubleshooting tips.
4. If your AI chat session dies, paste this README + the current chapter URL into a new chat and say *"I'm on Stage X, help me continue."* That's enough context.

---

## Document map

| # | Document | What you'll learn | Stage |
|---|----------|-------------------|-------|
| 00 | [Roadmap](docs/00-roadmap.md) | The full 4–6 week plan with milestones | All |
| 01 | [Architecture](docs/01-architecture.md) | How the app is wired together | Week 1 |
| 02 | [Local Development](docs/02-local-development.md) | Run the app on your laptop | Week 1 |
| 03 | [Feature Development](docs/03-feature-development.md) | Programming exercises (favorites, search, etc.) | Week 2 |
| 04 | [CI/CD Concepts](docs/04-cicd-guide.md) | What CI/CD is and how GitHub Actions works | Week 3 |
| 05 | [EC2 Manual Deployment](docs/05-deployment-ec2.md) | Ship it to a real cloud VM by hand | Week 3 |
| 06 | [Ansible Automation](docs/06-ansible-automation.md) | Automate the manual deploy | Week 3 |
| 07 | [Terraform IaC](docs/07-terraform-iac.md) | Provision infra as code | Week 4 |
| 08 | [Docker](docs/08-docker-containerization.md) | Containerize the app | Week 4 |
| 09 | [Observability](docs/09-observability.md) | Prometheus + Grafana dashboards | Week 5 |
| 10 | [Kubernetes](docs/10-kubernetes.md) *(optional)* | Run it on K8s | Week 6 |
| A1 | [Azure appendix](docs/appendix-azure.md) | AWS → Azure swap for Ch 05 + 07 | Optional parallel |
| — | [Git basics](docs/reference/git-basics.md) | Daily git workflow | Reference |
| — | [Bash basics](docs/reference/bash-basics.md) | Shell survival kit | Reference |
| — | [Troubleshooting](docs/reference/troubleshooting.md) | Common errors + fixes | Reference |
| — | [Resume tips](docs/reference/resume-tips.md) | How to talk about this project | Reference |

---

## Project structure

```
fortune-cookie/
├── README.md                 <- you are here
├── docs/                     <- all guides and reference material
├── backend/                  <- FastAPI app + SQLAlchemy models
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── routers/fortunes.py
│   ├── requirements.txt
│   └── seed_fortunes.py
└── frontend/                 <- React + Vite + Tailwind
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── FortuneCookie.jsx
    │   │   └── MessageHistory.jsx
    │   └── api.js
    └── package.json
```

---

## Quick start (TL;DR for impatient learners)

You should read [`docs/02-local-development.md`](docs/02-local-development.md) for the full explanation, but here's the speed-run:

```bash
# 1. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed_fortunes.py          # creates SQLite DB + seed rows
uvicorn app.main:app --reload    # http://localhost:8000/docs

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Click the cookie. It breaks. A fortune appears. Check the history panel for past fortunes. That's the MVP.

**AI integration:** if `OPENAI_API_KEY` is set in `backend/.env`, each fortune is generated fresh by an LLM and marked with a ✨ **AI** badge. If the key is missing, the app has a network issue, or OpenAI is down, the app silently falls back to a curated seed collection and shows a 📜 **Default** badge. You can clone the repo with zero setup and it still works.

---

## Guiding principles (how we work)

1. **Industry-standard tools only.** Nothing exotic. If a senior SRE wouldn't recognize it, it's not in here.
2. **Small steps, frequent commits.** You should `git commit` every time a small thing works.
3. **Docs first, ship second.** Every chapter is written so you can resume it a week later without guessing.
4. **Execution over theory.** We learn tools by using them, not by reading about them.
5. **Fail safely.** You'll break things. That's the job. Troubleshooting guides are in [`docs/reference/troubleshooting.md`](docs/reference/troubleshooting.md).

---

## End-state checklist

By the time you finish, this repo will have:

- [ ] A working FastAPI + React app with a cookie-breaking animation
- [ ] PostgreSQL persistence with Alembic-free manual schema (simple, good enough)
- [ ] At least 3 user-implemented features (favorites, search, pagination, etc.)
- [ ] A GitHub Actions workflow that **deploys** on push to `main`
- [ ] An Ansible playbook that provisions a fresh EC2 from zero to running app
- [ ] A Terraform module that creates the VPC/EC2/security groups
- [ ] A `docker-compose.yml` running the whole stack locally
- [ ] Prometheus scraping app metrics + a Grafana dashboard
- [ ] *(stretch)* A minimal K8s manifest set

That's a **strong mid-level SRE/DevOps portfolio** in one repo.

Now open [`docs/00-roadmap.md`](docs/00-roadmap.md) and let's go.

---

## How to get more help (ask the AI to extend anything)

These docs are a **scaffold** — if something feels thin, ask. Copy any of the prompts below into a chat with your AI assistant (Cursor / Claude / ChatGPT). Replace `<…>` with specifics.

### Common "please extend" requests

| If you want… | Ask literally this |
|--------------|-------------------|
| More programming exercises in Ch 03 | *"Add 5 more Tier-2 features to `docs/03-feature-development.md`, focused on backend validation and error handling."* |
| A line-by-line walkthrough of a file | *"Walk me through `deploy/site.yml` line by line, explaining each Ansible module like I'm new."* |
| A chapter condensed | *"Summarize `docs/07-terraform-iac.md` in one page for revision."* |
| A chapter expanded | *"Expand Ch 09 with 3 more Grafana panels and the PromQL behind each."* |
| A brand-new topic added | *"Add `docs/11-security-hardening.md`: UFW, fail2ban, SSH hardening, secrets rotation, TLS with Let's Encrypt."* |
| A code review | *"Review all files I changed in my last 3 commits for naming, error handling, and security. Be blunt."* |
| Swap a tool | *"Replace Ansible in Ch 06 with a plain bash deploy script — keep the same structure."* |
| Add tests | *"Add `docs/testing.md` covering pytest for the backend and Playwright for the frontend, with copy-paste examples."* |
| Cloud swap | *"Rewrite Ch 05 for GCP Compute Engine, same structure as `appendix-azure.md`."* |

### Resume / continue after a broken chat

If your AI context dies, start the next chat with:

> *"I'm working on the Fortune Cookie portfolio project. The master doc is `README.md`, the roadmap is `docs/00-roadmap.md`. I'm currently on **Stage `<N>`** in `docs/0<N>-…md`. Here's what I've completed: `<bullets>`. Please pick up where I left off — first, read the current chapter, then help me with `<next task>`."*

That's enough context for any competent AI to resume without re-reading everything.

### "This is broken" — the troubleshooting prompt

When something fails:

> *"I ran `<command>` and got this error: `<paste full error, including stack trace>`. Repo state: `<git rev-parse HEAD>`. Here's the file that's failing: `<paste file contents>`. What's wrong and how do I fix it?"*

Always include: the **full** error, the command, the file. Summarizing wastes your turn.

### Periodic code-quality checkpoint

At the end of each week, ask:

> *"I just finished Week `<N>`. Here's `git log --oneline main~10..main` and my current directory tree. Review for: (1) code quality, (2) missing best practices I should add before the next week, (3) anything I'd be embarrassed to show an interviewer."*

---

## A note on using AI well

- **Don't let it write code you haven't read.** If you can't explain it, you didn't learn it.
- **Paste errors verbatim.** AI is 10× better at debugging real output than summaries.
- **Ask for the "why", not just the "what".** `"Why use Pydantic over a dataclass here?"` is a better question than `"Fix this."`.
- **Push back when it's wrong.** If a suggestion doesn't make sense, say so. These tools aren't oracles.

