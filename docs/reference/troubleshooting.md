# Troubleshooting Playbook

> Read this when something's broken. Entries are grouped by **symptom first**, not by tool.

---

## The 5-step debugging checklist (do this EVERY time)

1. **Read the full error.** Copy it. Don't paraphrase.
2. **What changed?** Last commit, last config edit, last deploy.
3. **Which layer?** Browser / API / DB / infra. Work from outside in.
4. **Reproduce minimally.** Single `curl`, single click.
5. **Read the logs.** Then ask the AI, not before.

If you skip step 5 you will ask useless questions. AI + logs = 10× results vs AI alone.

---

## Frontend

### Blank page

- DevTools → Console for red text.
- DevTools → Network: is `/api/fortunes/random` red? Backend is down or proxy is wrong.
- `npm run dev` terminal — Vite prints errors here that don't show in the browser.
- Last resort: `rm -rf node_modules .vite && npm install && npm run dev`.

### CORS error

```
Access to fetch at 'http://…' has been blocked by CORS policy
```

- In dev: the Vite proxy should make CORS a non-issue. Is `vite.config.js` correct?
- In prod: the browser's origin (e.g. `http://1.2.3.4`) must be in `backend/.env`'s `CORS_ORIGINS`.
- Restart the backend after editing `.env` — changes aren't picked up live.

### Animation looks broken / Tailwind classes don't do anything

- Tailwind's JIT only includes classes it sees in `content:` globs. Check `tailwind.config.js`.
- If a class like `bg-[#ff0000]` doesn't work, the content glob isn't scanning that file.

---

## Backend

### `ModuleNotFoundError: No module named 'app'`

- You're running `uvicorn` from the wrong directory. Run from `backend/`.
- Your venv isn't activated. `source .venv/bin/activate`.

### `sqlalchemy.exc.OperationalError: no such table: fortunes`

- Forgot to run `python seed_fortunes.py` (which creates tables).
- Or you're pointing at a fresh DB that hasn't been migrated.

### `psycopg2.OperationalError: could not connect to server`

- Postgres isn't running: `sudo systemctl status postgresql`.
- Wrong port in `DATABASE_URL`.
- Password mismatch: `psql -h localhost -U fortune -d fortune` from the CLI to sanity check.

### 500 errors only on one endpoint

- `journalctl -u fortune -f` (prod) or look at the uvicorn terminal (dev).
- Copy the stack trace. The last line in *your code* (not the library) is where to start.

### Port already in use

```
[Errno 98] Address already in use
```

- Something else is on :8000. `sudo ss -tlnp | grep 8000`.
- Kill the zombie: `pkill -f uvicorn`.

---

## Database

### Seed script doesn't add anything

It's idempotent by design. Existing seed rows are skipped. To force re-seed: `DROP TABLE fortunes;` in `psql`, then rerun.

### SQLite → Postgres migration leaves you with an empty DB

Expected. SQLite file didn't come with you. Just re-run `python seed_fortunes.py` against the new `DATABASE_URL`.

### Postgres: `FATAL: password authentication failed`

- Wrong password in `.env`.
- On EC2: you changed the DB password on the server but forgot to update `.env` → restart the service.

---

## Docker

### Build is slow / keeps re-downloading deps

- Missing `.dockerignore` (node_modules being copied into the build context).
- Rearrange Dockerfile so that `COPY requirements.txt` + `pip install` comes **before** `COPY . .` — the install layer gets cached.

### Container exits immediately

```bash
docker ps -a                    # shows exited containers
docker logs <container>         # why did it exit
```

Most common: the main process crashed. Look for Python tracebacks or nginx config errors.

### "Connection refused" from frontend container → backend

- Are both services in the same docker-compose file? They auto-share a network.
- Did you use the **service name** (`backend:8000`) not `localhost:8000`? Inside a container, `localhost` is the container itself.

### Running out of disk (`no space left on device`)

```bash
docker system df                # see usage
docker system prune -af         # nuke unused images (careful)
docker volume prune             # nuke unused volumes (extra careful)
```

---

## Nginx

### 502 Bad Gateway

Backend is down or not reachable at the configured `proxy_pass`. Check:

```bash
sudo systemctl status fortune
curl http://127.0.0.1:8000/healthz
```

### 404 on `/api/*` but `/` works

`location /api/` block missing or malformed. Test config:

```bash
sudo nginx -t
```

### Nginx won't start after editing config

`sudo nginx -t` always before `reload`. Fix the reported line number.

---

## SSH

### `Permission denied (publickey)`

- Wrong key: `ssh -i ~/.ssh/correct-key.pem ubuntu@<ip>`.
- Wrong user: AWS Ubuntu AMIs use `ubuntu`, Amazon Linux uses `ec2-user`, Debian uses `admin`. Never `root`.
- Key file too open: `chmod 600 ~/.ssh/fortune-key.pem`.

### `Connection timed out`

- Security group: port 22 not open from your IP.
- Your IP changed (home ISP rotated it). Update the security group.
- Instance is stopped — check AWS console.

---

## Ansible

### `psycopg2` missing on target

The Postgres community modules need `python3-psycopg2` on the **target**. Add it to the apt install task before any postgres task runs.

### "skipping: no hosts matched"

Bad inventory group name in `hosts:`. Check `inventory.ini`.

### Always "changed" on the same task

Most often a `shell:`/`command:` task without `changed_when` or `creates:`. Prefer a native module (e.g. `copy`, `apt`) — they compute changed automatically.

---

## Terraform

### "Error: InvalidKeyPair.NotFound"

`var.key_name` must match the **AWS-console name** of the key pair, not the filename.

### Apply wants to destroy + recreate something unexpectedly

Read the plan output carefully. A `-/+` means "replace". Find the attribute in red forcing the recreation. Usually AMI changed or a tag was added.

### State file corruption / "state lock"

For this solo project with local state, just: `rm .terraform.tfstate.lock.info` if Terraform hangs on lock. Not safe in teams — different story.

---

## GitHub Actions

### Workflow doesn't trigger

- File must be at `.github/workflows/*.yml` exactly.
- `on:` must match your event (pushing to `main`, not `master`).
- Syntax error — GitHub will show it under Actions → your workflow → "Invalid workflow".

### Secret is empty / `"${{ secrets.FOO }}"` is blank

- You added the secret in the wrong scope (environment vs repo vs org).
- You typoed the name.
- The workflow is running on a PR from a fork (secrets don't ship to fork PRs — by design).

### SSH step fails

- Private key secret must include the `-----BEGIN...-----` and `-----END...-----` lines and the newlines inside.
- File permissions: `chmod 600` after writing the key in the runner.

---

## Prometheus / Grafana

### Prometheus target is DOWN

- Go to Status → Targets. The error message says why (connection refused, wrong path, TLS mismatch).
- Is your backend service named `backend` inside the compose network? The scrape target must match.

### Grafana panel is empty

- Pick the right time range (top right). Default is often "last 6 hours" and you just started.
- Run the PromQL directly in Prometheus UI (http://…:9090) to confirm it returns data.
- Check that the **datasource** on the panel is the right one.

---

## Network (general)

```bash
# Is the remote port even reachable?
nc -zv example.com 443
telnet example.com 80

# What IP is a hostname resolving to?
dig +short example.com

# What IP am I?
curl -s https://checkip.amazonaws.com
```

---

## Last-resort moves

1. **Reboot it.** `sudo reboot` (EC2), `docker compose restart`, `systemctl restart …`.
2. **Delete and recreate.** That's literally what Ansible + Terraform are *for*.
3. **Ask the AI with the full error.** Don't summarize — paste the raw trace.
4. **Walk away for 10 minutes.** Then re-read the error.
5. **Sleep on it.** Morning-you is 2× smarter than night-you.
