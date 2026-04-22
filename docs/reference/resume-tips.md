# Resume & Interview Tips

> This project is the evidence. Your resume is the index. Don't hide the evidence.

---

## The 3-bullet version (paste into resume)

Replace `<X>` with your numbers after finishing.

> **Fortune Cookie Generator** — full-stack portfolio project.
> `FastAPI · PostgreSQL · React · Docker · GitHub Actions · Ansible · Terraform · AWS EC2 · Prometheus · Grafana`
>
> - Containerized a FastAPI + React + PostgreSQL stack with multi-stage Docker builds; final images under 200 MB, pinned base images, non-root users.
> - Provisioned AWS infra (VPC, SG, EC2, Elastic IP) with Terraform, configured with Ansible, deployed on every push to `main` via GitHub Actions — mean deploy time <X> minutes, zero-touch rollback by re-tagging the previous image SHA.
> - Instrumented the API with Prometheus, built Grafana dashboards covering the four golden signals, and added an error-rate alert triggered at >5% for 5 minutes.

Three bullets, ten tools, no fluff. That's the format hiring managers skim.

---

## GitHub repo polish checklist

- [ ] README has a one-line description **and** a GIF or screenshot above the fold.
- [ ] README opens with *what it does* before *how to run it*.
- [ ] `docs/` folder is visible and organized.
- [ ] At least one commented GitHub Actions run is green on `main`.
- [ ] Releases tab has at least one tag (`v0.1.0`).
- [ ] `About` section on GitHub repo page has a description + topic tags (`fastapi`, `react`, `docker`, `terraform`, `ansible`, `devops`, `sre`, `portfolio`).
- [ ] Pin the repo on your GitHub profile.

---

## Interview talking points (rehearse each one in 60 seconds)

### "Walk me through this project"

> "I built a small full-stack app — a fortune cookie generator — specifically to learn the SRE toolchain end-to-end. The code is a FastAPI backend with Postgres and a React frontend. But the *point* of the project is everything around the code: I Dockerized it, wrote a Terraform module that provisions the AWS infra, an Ansible playbook that configures the host, and a GitHub Actions pipeline that builds images and deploys on push to main. Then I added Prometheus metrics and a Grafana dashboard for the four golden signals."

### "Why did you choose X?"

Have one sentence for every tool:
- **FastAPI**: modern Python, typed, auto-generates OpenAPI docs.
- **Tailwind**: industry default; didn't want to fight a component library.
- **SQLAlchemy 2.0**: current idiomatic style, typed with `Mapped[]`.
- **Terraform not CloudFormation**: portable across clouds, larger community.
- **Ansible not shell**: idempotent, readable, built-in modules handle edge cases.
- **Docker Compose then K8s**: Compose is enough for a single VM; K8s is where I'd go for multi-host or horizontal scaling.
- **Prometheus not CloudWatch**: learn the OSS standard; CloudWatch is a vendor-specific wrapper.

### "What would you do differently?"

Genuine, humble answer = credibility.
- "I'd use Alembic migrations from day one instead of `create_all`."
- "I'd split state into S3 + DynamoDB for Terraform — I used local state because it's a solo project."
- "I'd add a staging environment. I didn't for cost, but prod-only is a production smell."

### "How would you scale this?"

Step-by-step, bigger steps at the end:
1. Put a load balancer in front of multiple backend instances (auto-scaling group).
2. Split the DB onto its own instance or RDS.
3. Add read replicas if the query mix is read-heavy.
4. Cache `/api/fortunes/random` in Redis.
5. Move to K8s when instance count > ~5.
6. Split services only when teams split.

### "How do you know it's broken?"

Four golden signals. "My Grafana dashboard alerts on error rate > 5% for 5 min. In a real team, that alert would page on-call via Alertmanager → Slack → PagerDuty."

### "Walk me through a debugging session"

Pick a real bug you hit during the project. Be specific. Something like:
> "After switching from SQLite to Postgres my random endpoint started returning 500s. I tailed the uvicorn journal — it was a `func.random()` dialect mismatch because I'd hardcoded something. I read the SQLAlchemy docs for `func.random()` vs `func.rand()`, confirmed Postgres uses `RANDOM()`, found my SQL was fine, realized it was actually a psycopg2 connection issue, fixed the connection string, added a healthcheck so this fails loudly in CI/CD next time."

**A real story with a real tool beats 10 generic "I'm detail-oriented" claims.**

---

## Anti-patterns to avoid

- Listing 20 tools you "used" for 10 minutes each. Go deep on the few you built with.
- Copy-pasting project description verbatim from this doc. Rewrite in your voice.
- Hiding the AI's help. It's normal; say "I used AI as a pair programmer and code reviewer."
- Blowing up your GitHub with `Initial commit` x200 right before applying for jobs. Small, meaningful commits throughout > a burst at the end.

---

## Which roles to apply for

This project is evidence for:

- **Junior/Associate SRE**
- **Junior/Associate DevOps Engineer**
- **Cloud Engineer I**
- **Platform Engineer (Junior)**

Not (yet) for:
- **Senior** anything. Those need production experience, not projects.
- **Backend Engineer** roles where they want deep Django/Node specialists. You'll look undersized.

---

## The short cover letter template

> I'm applying for <role>. I recently built and documented <Fortune Cookie repo URL> end-to-end: Python + React behind Nginx, containerized, provisioned via Terraform, configured via Ansible, deployed via GitHub Actions to AWS, observed via Prometheus + Grafana. The project was specifically designed to practice the SRE toolchain cohesively rather than tool-by-tool. The docs/ folder contains the full engineering log.
>
> Happy to walk through any chapter — feedback on what I'd do differently is always welcome.

Three sentences, one link, zero fluff. It gets read.
