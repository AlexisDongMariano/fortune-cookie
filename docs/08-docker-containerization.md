# 08 — Docker + Docker Compose

> Goal: replace the "install python, install node, install postgres" ceremony with **one command**: `docker compose up`.
> Then deploy the same containers to EC2.

---

## Why containers

| Without Docker | With Docker |
|----------------|-------------|
| "Works on my laptop" | "Works anywhere Docker runs" |
| Manual OS setup on every machine | Dockerfile is the setup |
| Version drift between devs | Pinned base images + pinned deps |
| Rollback = re-deploy old code | Rollback = pull old image tag |

For an SRE role, **Docker is non-negotiable**. Learn it well.

---

## Install Docker

```bash
# Ubuntu/WSL — official convenience script (fine for dev)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker                     # or log out/in

# macOS — use Docker Desktop
# brew install --cask docker ; then launch the app once

docker --version
docker compose version            # note: "docker compose" with space, not "docker-compose"
```

---

## The plan

Three images:

1. **backend** — FastAPI + uvicorn
2. **frontend** — nginx serving the built React files
3. **postgres** — official image, no changes

One `docker-compose.yml` wires them together.

---

## 1. Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1.7

# --- Stage 1: install deps into a virtualenv ---
FROM python:3.12-slim AS deps
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# --- Stage 2: runtime image ---
FROM python:3.12-slim AS runtime
WORKDIR /app

# non-root user (security best practice)
RUN useradd --create-home --shell /usr/sbin/nologin app
COPY --from=deps /opt/venv /opt/venv
COPY . /app
RUN chown -R app:app /app
USER app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `backend/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.env
*.db
tests/
```

Build and test:

```bash
cd backend
docker build -t fortune-backend:dev .
docker run --rm -p 8000:8000 -e DATABASE_URL=sqlite:///./fortune.db fortune-backend:dev
# in another shell
curl http://localhost:8000/healthz
```

---

## 2. Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1.7

# --- Stage 1: build the React app ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Stage 2: serve static files with nginx ---
FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    # Proxy /api to the backend service defined in docker-compose.
    # "backend" resolves via Docker's built-in DNS.
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /healthz {
        proxy_pass http://backend:8000/healthz;
    }
}
```

Create `frontend/.dockerignore`:

```
node_modules/
dist/
.vite/
```

---

## 3. `docker-compose.yml` (repo root)

```yaml
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: fortune
      POSTGRES_PASSWORD: ${DB_PASSWORD:-fortune}
      POSTGRES_DB: fortune
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fortune"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build: ./backend
    image: fortune-backend:${TAG:-dev}
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+psycopg2://fortune:${DB_PASSWORD:-fortune}@db:5432/fortune
      CORS_ORIGINS: http://localhost,http://localhost:8080
    depends_on:
      db:
        condition: service_healthy
    # one-shot seed: runs on first start, idempotent
    command: >
      sh -c "python seed_fortunes.py &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

  frontend:
    build: ./frontend
    image: fortune-frontend:${TAG:-dev}
    restart: unless-stopped
    ports:
      - "8080:80"        # http://localhost:8080
    depends_on:
      - backend

volumes:
  db_data:
```

Run the whole stack:

```bash
docker compose up --build
```

Open http://localhost:8080. Cookie cracks. You have not installed Python, Node, or Postgres on your laptop (well, the host — the containers have them).

`Ctrl-C` to stop. `docker compose down` to remove containers. `docker compose down -v` to also delete the DB volume.

---

## 4. Image hygiene (what interviewers ask about)

| Practice | Why |
|----------|-----|
| Multi-stage builds | Final image doesn't ship build tools |
| Non-root `USER` | If the app is compromised, attacker can't `apt-get install` |
| Pin base image (`3.12-slim` not `latest`) | Reproducible builds |
| `.dockerignore` | Faster builds, smaller context |
| `HEALTHCHECK` | Orchestrators can restart unhealthy containers |
| One process per container | The Docker way; makes logs + restarts clean |
| No secrets in `Dockerfile` | Use env vars at runtime, or a secrets manager |

Check your image size:

```bash
docker images fortune-backend:dev
# 120-150MB is the target. 1GB means you shipped build tools.
```

---

## 5. Pushing to a registry

Pick one:

- **Docker Hub** (easiest): https://hub.docker.com — free for public.
- **GitHub Container Registry** (GHCR): integrated with GitHub Actions, great default.
- **Amazon ECR**: tightest AWS integration, a bit more setup.

**GHCR example** (we'll use this):

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <you> --password-stdin
docker tag fortune-backend:dev ghcr.io/<you>/fortune-backend:$(git rev-parse --short HEAD)
docker push ghcr.io/<you>/fortune-backend:$(git rev-parse --short HEAD)
```

**Rule:** tag with the git SHA, not `latest`. `latest` is a footgun in prod.

---

## 6. Deploy containers to the EC2 (replaces Chapter 06 workflow)

Now the EC2 doesn't need Python, Node, or Postgres installed — just Docker.

Simplified Ansible playbook (`deploy/site-docker.yml`):

```yaml
- name: Deploy fortune via docker compose
  hosts: web
  become: true

  tasks:
    - name: Install docker
      shell: |
        if ! command -v docker >/dev/null; then
          curl -fsSL https://get.docker.com | sh
          usermod -aG docker ubuntu
        fi
      args: { executable: /bin/bash }
      changed_when: false

    - name: Ensure app dir
      file: { path: /srv/fortune, state: directory, owner: ubuntu }

    - name: Copy compose file
      copy:
        src: ../docker-compose.prod.yml
        dest: /srv/fortune/docker-compose.yml
        owner: ubuntu

    - name: Copy env file
      template:
        src: env.j2
        dest: /srv/fortune/.env
        owner: ubuntu
        mode: "0600"

    - name: Pull images
      become_user: ubuntu
      command: docker compose pull
      args: { chdir: /srv/fortune }

    - name: Up
      become_user: ubuntu
      command: docker compose up -d
      args: { chdir: /srv/fortune }
```

Create `docker-compose.prod.yml` — same as dev but using pushed images:

```yaml
services:
  db:
    image: postgres:16
    # ...same as dev...

  backend:
    image: ghcr.io/<you>/fortune-backend:${TAG}
    # no build, no command override — image already bakes that in
    restart: unless-stopped
    env_file: .env
    depends_on:
      db: { condition: service_healthy }

  frontend:
    image: ghcr.io/<you>/fortune-frontend:${TAG}
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on: [backend]

volumes:
  db_data:
```

---

## 7. Updated GitHub Actions workflow

`.github/workflows/deploy.yml` — replaces the non-Docker version:

```yaml
name: Build & Deploy

on:
  push:
    branches: [main]

jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      tag: ${{ steps.tag.outputs.tag }}
    steps:
      - uses: actions/checkout@v4
      - id: tag
        run: echo "tag=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/fortune-backend:${{ steps.tag.outputs.tag }}

      - uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/fortune-frontend:${{ steps.tag.outputs.tag }}

  deploy:
    needs: build-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install -y ansible
      - run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.EC2_SSH_KEY }}" > ~/.ssh/deploy.pem
          chmod 600 ~/.ssh/deploy.pem
      - env:
          TAG: ${{ needs.build-push.outputs.tag }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          ANSIBLE_HOST_KEY_CHECKING: "False"
        run: |
          ansible-playbook \
            -i "${{ secrets.EC2_HOST }}," \
            -u ${{ secrets.EC2_USER }} \
            --private-key ~/.ssh/deploy.pem \
            --extra-vars "tag=$TAG db_password=$DB_PASSWORD" \
            deploy/site-docker.yml
      - run: sleep 10 && curl -fsS http://${{ secrets.EC2_HOST }}/healthz
```

Now **every push** builds new images, pushes them, and redeploys. And rollback is:

```bash
# on the EC2, or via a small GH Action
docker compose pull ghcr.io/<you>/fortune-backend:<previous-sha>
TAG=<previous-sha> docker compose up -d
```

---

## 8. Quick debugging commands

```bash
docker ps                         # what's running
docker logs -f <container>        # tail logs
docker compose logs -f backend    # same, by service name
docker exec -it <container> sh    # shell inside
docker inspect <container>        # full config dump
docker system df                  # disk usage
docker system prune -af           # nuke unused images/containers (careful)
```

---

## Definition of Done

- [ ] `docker compose up` locally → app works at http://localhost:8080.
- [ ] Backend image < 200 MB; frontend image < 60 MB.
- [ ] Images pushed to GHCR (or ECR/Docker Hub).
- [ ] EC2 now runs the containers (not systemd processes).
- [ ] Rollback to a previous SHA works.

Next: [`09-observability.md`](09-observability.md).
