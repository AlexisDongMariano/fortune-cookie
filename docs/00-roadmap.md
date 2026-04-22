# 00 — Roadmap (4–6 Week Plan)

> **Audience:** aspiring DevOps/SRE with ~1–3 hours per day, little tool experience.
> **Goal:** ship a public, production-shaped portfolio project and be able to speak about every piece in a job interview.

---

## How to read this doc

- Each week has a **theme**, **deliverables**, and a **Definition of Done (DoD)** checklist.
- Stages map 1:1 to the numbered docs in this folder (`01-…`, `02-…`, etc.).
- If you fall behind, **skip the "stretch" items first** — never skip the DoD.
- If a chat with your AI assistant dies: tell it *"I'm on Stage N in `docs/0N-…md`, resume me"* and paste the README.

---

## Big picture

```
Week 1: Code it locally        -> App runs on your laptop
Week 2: Extend it              -> You write 3+ features yourself
Week 3: Ship it                -> Manual EC2 deploy + Ansible + GH Actions CD
Week 4: Harden it              -> Docker + Terraform (infra as code)
Week 5: See it                 -> Prometheus + Grafana metrics & dashboard
Week 6: Scale it (stretch)     -> Kubernetes + wrap-up + resume polish
```

---

## Week 1 — "Make it run" (Stages 01 + 02)

**Daily budget: 1–2 h**

| Day | Task | Time |
|-----|------|------|
| 1 | Install prerequisites (Python 3.11+, Node 20+, git). Create GitHub repo. | 45 min |
| 2 | Read `01-architecture.md` end-to-end. Draw the diagram on paper. | 30 min |
| 3 | Follow `02-local-development.md`: run the backend. Hit `/healthz` with curl. | 60 min |
| 4 | Install frontend deps. `npm run dev`. See the cookie. | 60 min |
| 5 | Click the cookie. Check the history list. Favorite a message. | 30 min |
| 6 | Read the code top-to-bottom: `main.py`, `models.py`, `fortunes.py`, `App.jsx`. | 90 min |
| 7 | Make **any** small change (e.g. change title color) and commit + push. | 30 min |

**Definition of Done:**
- [ ] Repo is public on GitHub.
- [ ] App runs locally; cookie animation works.
- [ ] You can explain, out loud, what happens when the cookie is clicked (browser → API → DB → back).
- [ ] You've made at least 3 git commits with meaningful messages.

**Checkpoint (ask your AI):** *"Review my commit history and architecture understanding. Is my explanation correct?"*

---

## Week 2 — "Extend it" (Stage 03)

**Daily budget: 1–2 h. This is where real learning happens.**

Pick at least **3** features from `03-feature-development.md`. Suggested starter set:

1. **Favorites page** — a new route that lists only `is_favorite=true` fortunes.
2. **Search** — a query param on `GET /api/fortunes` that filters by substring.
3. **Add-your-own** — UI form that POSTs a new seed fortune.

Implement them yourself. Use the AI as a *pair programmer*, not a ghostwriter:
- Ask it to **explain errors**.
- Ask it to **review your diff**.
- Ask "what's idiomatic here?" before committing.

**Definition of Done:**
- [ ] 3 features merged as separate PRs (yes, PRs to your own repo — it's practice).
- [ ] Each PR has a description explaining *what* and *why*.
- [ ] You can demo all features in under 2 minutes.

**Checkpoint:** *"Review my 3 PRs for code quality, naming, and error handling."*

---

## Week 3 — "Ship it" (Stages 04 + 05 + 06)

This is the **DevOps core** week. Expect to get stuck. Budget more time.

| Day | Task | Doc |
|-----|------|-----|
| 1 | Read the CI/CD overview. Understand what CD means. | `04-cicd-guide.md` |
| 2 | Create AWS account (free tier). Launch an EC2 t3.micro. SSH in. | `05-deployment-ec2.md` §1–2 |
| 3 | Install Python + Node + Postgres on the EC2 by hand. | `05-…` §3 |
| 4 | Run the app on EC2 using `systemd`. Nginx reverse proxy. | `05-…` §4–5 |
| 5 | Point a browser at your EC2 public IP. Celebrate. | — |
| 6 | Rewrite the manual steps as an Ansible playbook. | `06-ansible-automation.md` |
| 7 | Add a GitHub Actions workflow that SSHs in and runs the playbook. | `06-…` §4 |

**Definition of Done:**
- [ ] App reachable on a public IP (or Elastic IP / domain).
- [ ] `git push main` → auto-deploys.
- [ ] `ansible-playbook site.yml` rebuilds a fresh EC2 to the same state.
- [ ] You've deleted and re-created the EC2 at least once to prove the playbook works.

**Checkpoint:** *"Destroy my EC2 and restore it with my playbook. Walk me through what happens if it fails."*

---

## Week 4 — "Infra as code + containers" (Stages 07 + 08)

| Day | Task |
|-----|------|
| 1–2 | Terraform: VPC, subnet, SG, EC2, Elastic IP. |
| 3   | `terraform destroy` + `terraform apply` end-to-end to prove reproducibility. |
| 4   | Write `Dockerfile` for backend and frontend. |
| 5   | Write `docker-compose.yml` (backend + frontend + postgres). |
| 6   | Run the compose stack locally. Push images to Docker Hub (or ECR). |
| 7   | Swap the Ansible-installed app for a Docker Compose deploy on EC2. |

**Definition of Done:**
- [ ] `terraform apply` creates all infra from scratch.
- [ ] `docker compose up` runs the whole app on your laptop with zero manual steps.
- [ ] Production EC2 runs containers, not raw processes.

**Checkpoint:** *"Read my Dockerfile and tell me 3 ways to make the image smaller or safer."*

---

## Week 5 — "Observability" (Stage 09)

| Day | Task |
|-----|------|
| 1 | Add `prometheus-fastapi-instrumentator` to the backend. See `/metrics`. |
| 2 | Run Prometheus in docker-compose and scrape your API. |
| 3 | Run Grafana in docker-compose. Wire it to Prometheus. |
| 4 | Build a dashboard: request rate, p95 latency, error rate, DB query count. |
| 5 | Add 1 alert (e.g. "error rate > 5% for 5 min"). |
| 6 | Document the dashboard in `docs/09-…` with a screenshot. |
| 7 | Rest / catch-up day. |

**Definition of Done:**
- [ ] `/metrics` returns Prometheus-format data.
- [ ] Grafana dashboard shows live traffic when you click the cookie.
- [ ] Dashboard JSON is checked into the repo.
- [ ] Screenshot is in the README.

**Checkpoint:** *"Look at my Grafana panels and suggest one more that would matter in production."*

---

## Week 6 — "Scale it" (Stage 10, optional) + Wrap-up

**Optional K8s track:**
- Deploy your containers to a local `kind` or `minikube` cluster.
- Write Deployments, Services, and one Ingress.
- Bonus: Helm chart.

**Portfolio wrap-up (mandatory):**
- Polish the README: add screenshots + a GIF of the cookie breaking.
- Write a blog-style post in `docs/retrospective.md`: what you learned, what broke, what you'd do differently.
- Update your resume using `reference/resume-tips.md`.
- Pin the repo on your GitHub profile.

**Definition of Done:**
- [ ] README has a header image and clear "what is this" paragraph.
- [ ] Resume updated with 3 bullet points citing concrete tools from this project.
- [ ] You can give a 5-minute walkthrough of the project from memory.

---

## Milestones at a glance

| # | Milestone | Week | Evidence |
|---|-----------|------|----------|
| M1 | App runs locally | 1 | Screenshot of cookie + history |
| M2 | 3 user-built features shipped | 2 | 3 merged PRs |
| M3 | Auto-deploys on push to main | 3 | Green GH Actions run + live URL |
| M4 | Infra rebuildable from scratch | 4 | `terraform apply` + `docker compose up` |
| M5 | Metrics + dashboard | 5 | Grafana JSON + screenshot |
| M6 | K8s or polish | 6 | K8s manifests or resume + retrospective |

---

## Evaluation criteria (self-grade at the end)

Rate yourself 1–5 on each:

- **Clarity:** can a stranger clone the repo and run it in 10 minutes?
- **Reproducibility:** can you wipe the cloud and rebuild it with `terraform apply && ansible-playbook`?
- **Ownership:** did you write the code, or did the AI? (be honest)
- **Debuggability:** when it broke, did you read logs + fix it yourself?
- **Communication:** is the docs folder something you'd be proud to show?

Target: 4+/5 on every line. If something is a 2–3, go back and fix it — that's your next learning opportunity.

---

## Pacing rules (read these twice)

1. **Commit every time something small works.** Small commits = easy rollback = sane git history.
2. **Write the doc *before* you automate.** If you can't describe it in prose, you can't automate it reliably.
3. **Three-strikes rule:** if you're stuck for 3 tries and >30 min, ask the AI, or take a walk, or both.
4. **Time-box exploration.** 20 min of research max before you make a choice and move on.
5. **Never deploy on a Friday evening.** Old but true.

Next: open [`01-architecture.md`](01-architecture.md).
