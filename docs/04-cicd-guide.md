# 04 — CI/CD Concepts

> This chapter is **concept-only**. The doing happens in Stages 05–08. We cover enough theory so you can talk about CI/CD in an interview.

---

## One-paragraph definition

**CI** (Continuous Integration) = every `git push` automatically builds and tests your code.
**CD** (Continuous Delivery / Deployment) = if the build is green, your code is automatically shipped to an environment. *Delivery* = ready to deploy with one click. *Deployment* = actually deployed.

This project focuses on **CD**. We deploy on every push to `main`. Tests/CI are optional (see §5).

---

## Why it matters

Without CI/CD:
- "Works on my machine."
- "Who deployed to prod last?"
- 3 AM rollbacks done over SSH.

With CI/CD:
- The pipeline is the source of truth.
- Anyone can ship with `git push`.
- Rollbacks are `git revert && push`.

This is 80% of what DevOps teams *actually* build. Learning it well beats knowing 5 exotic tools.

---

## The pipeline shape we'll build

```
┌──────────────┐   push    ┌─────────────────────────────────┐   SSH   ┌─────────┐
│  your laptop │──────────▶│  GitHub Actions runner          │────────▶│   EC2   │
└──────────────┘           │                                 │         │         │
                           │  1. checkout                    │         │  pulls  │
                           │  2. (optional) lint + test      │         │  runs   │
                           │  3. ssh + run ansible playbook  │         │   app   │
                           └─────────────────────────────────┘         └─────────┘
```

In Week 4 we'll add a "build Docker image" step and replace "ssh + ansible" with "ssh + docker compose pull && up".

---

## Key concepts you must know (interview-ready)

### 1. Artifacts
The thing the pipeline *produces*. For us: a Docker image (Week 4) or a git commit (Week 3).
Tag it with the **git SHA**, never just `latest`.

### 2. Environments
`dev` → `staging` → `prod`. For this project we cheat and only have `prod` on EC2. That's fine to say in an interview — "I ran one env because of cost; I'd add staging as the next step."

### 3. Secrets
Never commit them. GitHub Actions has **repository secrets** (`Settings → Secrets and variables → Actions`). We'll use:
- `EC2_HOST`, `EC2_USER`
- `EC2_SSH_KEY` (the private key, multiline)
- `DATABASE_URL` (for CD to write to the EC2's env)

### 4. Idempotency
Running the pipeline twice should produce the same result. Ansible (Week 3) and Terraform (Week 4) bake this in. Shell scripts don't — which is why we don't ship with raw bash.

### 5. Fail fast
Pipelines should fail on the first broken step, loudly. `set -euo pipefail` in bash. `fail-fast: true` in GH Actions (the default).

### 6. Rollbacks
Two strategies:
- **git revert**: revert the bad commit → push → pipeline deploys the previous code.
- **pin to previous image tag**: change the tag in your compose file → push → pipeline pulls old image.

Both are fine. Mention both in interviews.

---

## GitHub Actions in 60 seconds

A workflow is a YAML file at `.github/workflows/deploy.yml` (or any name ending in `.yml`).

Minimal skeleton:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying commit $GITHUB_SHA"
```

**Vocabulary:**
- **workflow**: the YAML file.
- **job**: a group of steps that run on one runner (VM).
- **step**: a single shell command or a reusable `action` (like `actions/checkout@v4`).
- **runner**: the VM GitHub gives you (free: 2000 min/month on public repos).

That's the whole mental model. Everything else is configuration details.

---

## Our actual deploy workflow (preview — you'll build it in Stage 06)

```yaml
name: Deploy to EC2

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Ansible
        run: sudo apt-get update && sudo apt-get install -y ansible

      - name: Write SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.EC2_SSH_KEY }}" > ~/.ssh/deploy.pem
          chmod 600 ~/.ssh/deploy.pem
          ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts

      - name: Run playbook
        env:
          ANSIBLE_HOST_KEY_CHECKING: "False"
        run: |
          ansible-playbook -i "${{ secrets.EC2_HOST }}," \
            --private-key ~/.ssh/deploy.pem \
            -u ${{ secrets.EC2_USER }} \
            deploy/site.yml
```

Stop here — this is just a preview. You'll build and understand it in Stage 06.

---

## Optional: CI (tests) guidance

If you ever want to add CI, the standard shape is:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt pytest httpx
      - run: pytest
        working-directory: backend

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
```

This is genuinely 30 minutes of work when you're ready. Don't overthink it.

---

## Checklist of things an interviewer might ask

- "What's the difference between CI and CD?" → see §1.
- "How do you roll back a bad deploy?" → `git revert` or re-tag previous image.
- "How do you handle secrets in a pipeline?" → GH Actions secrets, never committed.
- "How would you add staging?" → a second EC2 (or namespace), gate prod behind a manual `workflow_dispatch` or an `environment: production` requiring approval.
- "Why Ansible not a shell script?" → idempotency, inventory, modules handle edge cases (e.g. `apt` knows if a package is already installed).
- "How do you keep deploys fast?" → cache deps, only rebuild what changed, small images.

---

## Definition of Done

- [ ] You can explain in your own words what a "job" vs "step" is in GitHub Actions.
- [ ] You know where secrets live and where they don't (never in git).
- [ ] You've drawn the pipeline diagram above on paper.

Next: [`05-deployment-ec2.md`](05-deployment-ec2.md) — hands-on time.
