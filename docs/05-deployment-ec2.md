# 05 — EC2 Manual Deployment

> Goal: **deploy the app by hand, once**, to understand every piece. Then (Stage 06) Ansible will automate what you just did.
>
> You'll spend ~$0 during the free tier. A `t3.micro` running 24/7 = ~$8/month if you forget to stop it. **Set a billing alarm** (see §1.5).
>
> **Prefer Azure?** Use [`appendix-azure.md`](appendix-azure.md) **Part A** in place of this chapter. Chapters 06, 08, 09, 10 are cloud-agnostic.

---

## 0. What you'll build

```
                       ┌──────────────────────────────────┐
                       │   EC2 instance (Ubuntu 24.04)    │
                       │                                  │
Browser ──HTTP:80──▶  │   Nginx   ──reverse-proxy──▶    │
                       │             :80          :8000   │
                       │                                  │
                       │     Uvicorn (systemd unit)       │
                       │                │                 │
                       │                ▼                 │
                       │     PostgreSQL :5432             │
                       │                                  │
                       │   React build served as static   │
                       │   files from /var/www/fortune    │
                       └──────────────────────────────────┘
```

Everything on **one VM**. Good enough for a portfolio project. Splitting into 3 VMs (DB / API / web) is a Week 6+ exercise.

---

## 1. AWS account + billing guardrails (first-time only)

1. Create an AWS account: https://aws.amazon.com/free — real credit card, but stays within the free tier.
2. In the root account, **enable MFA** (Security Credentials → Assign MFA).
3. Create a billing alarm — this is the #1 mistake junior engineers make.
   - Billing → Budgets → Create budget → "Monthly" → **$5** threshold → email.
4. Create an **IAM user** for daily use (don't work as root):
   - IAM → Users → Create user → `fortune-dev` → Attach `AdministratorAccess` (fine for a learning account) → console access.
5. Create an **SSH key pair** in the region you'll use (e.g. `us-east-1`):
   - EC2 → Key Pairs → Create → name it `fortune-key` → download `fortune-key.pem`.
   - `chmod 600 ~/Downloads/fortune-key.pem` and move it to `~/.ssh/`.

---

## 2. Launch the EC2 (UI walkthrough, ~5 min)

EC2 → Launch instance:

| Setting | Value |
|---------|-------|
| Name | `fortune-dev` |
| AMI | **Ubuntu Server 24.04 LTS** (x86_64) |
| Instance type | `t3.micro` (free tier eligible) |
| Key pair | `fortune-key` (created above) |
| VPC | default |
| Subnet | any (leave default) |
| Public IP | **Enable** |
| Security group | create new, rules below |
| Storage | 20 GiB gp3 |

**Security group (critical)** — this is the firewall:

| Type | Protocol | Port | Source | Why |
|------|----------|------|--------|-----|
| SSH  | TCP      | 22   | My IP  | you only |
| HTTP | TCP      | 80   | 0.0.0.0/0 | public web |
| HTTPS| TCP      | 443  | 0.0.0.0/0 | future (cert in stretch) |

**Launch.** Copy the Public IPv4 address.

---

## 3. First SSH in

```bash
ssh -i ~/.ssh/fortune-key.pem ubuntu@<EC2_PUBLIC_IP>
```

If it hangs: security group is wrong.
If it asks for a password: key is wrong.
If it says "permissions too open": `chmod 600 ~/.ssh/fortune-key.pem`.

Once in:

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

---

## 4. Install the stack on the EC2

### 4.1 System deps

```bash
sudo apt-get install -y python3-venv python3-pip nodejs npm postgresql nginx git
```

Check versions:

```bash
python3 --version   # 3.12.x on 24.04
node --version      # 18.x — too old for us. Install Node 20 from NodeSource:
```

Install Node 20 (official NodeSource repo — the industry-standard way):

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version      # should now say v20.x
```

### 4.2 Create the database

```bash
sudo -u postgres psql <<'SQL'
CREATE USER fortune WITH PASSWORD 'changeme_before_prod';
CREATE DATABASE fortune OWNER fortune;
GRANT ALL PRIVILEGES ON DATABASE fortune TO fortune;
SQL
```

Test:

```bash
psql -h localhost -U fortune -d fortune -c "SELECT now();"
# Ctrl-D to exit if it drops you in
```

### 4.3 Clone + install the app

```bash
sudo mkdir -p /srv/fortune
sudo chown ubuntu:ubuntu /srv/fortune
cd /srv/fortune
git clone https://github.com/<you>/fortune-cookie.git .
```

Backend:

```bash
cd /srv/fortune/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > .env <<EOF
DATABASE_URL=postgresql+psycopg2://fortune:changeme_before_prod@localhost:5432/fortune
CORS_ORIGINS=http://<EC2_PUBLIC_IP>,https://<EC2_PUBLIC_IP>

# Optional: enable AI-generated fortunes. Leave blank to use seed messages.
# Get a key at https://platform.openai.com/api-keys
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=5
EOF

python seed_fortunes.py
```

Sanity check (Ctrl-C after 5s):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend (build static files):

```bash
cd /srv/fortune/frontend
npm ci
npm run build                  # outputs to dist/
sudo mkdir -p /var/www/fortune
sudo cp -r dist/* /var/www/fortune/
```

---

## 5. Run FastAPI via systemd (the Linux-native way)

Create `/etc/systemd/system/fortune.service`:

```bash
sudo tee /etc/systemd/system/fortune.service >/dev/null <<'UNIT'
[Unit]
Description=Fortune Cookie API
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/srv/fortune/backend
EnvironmentFile=/srv/fortune/backend/.env
ExecStart=/srv/fortune/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fortune
sudo systemctl status fortune           # should show "active (running)"
curl http://127.0.0.1:8000/healthz       # → {"status":"ok"}
```

Logs (memorize this — you will need it):

```bash
sudo journalctl -u fortune -f           # -f = follow, like tail
```

---

## 6. Nginx reverse proxy

Replace the default site:

```bash
sudo tee /etc/nginx/sites-available/fortune >/dev/null <<'NGINX'
server {
    listen 80 default_server;
    server_name _;

    root /var/www/fortune;
    index index.html;

    # React SPA — send every non-API route to index.html
    location / {
        try_files $uri /index.html;
    }

    # Forward API calls to the FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /healthz {
        proxy_pass http://127.0.0.1:8000/healthz;
    }
}
NGINX

sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/fortune /etc/nginx/sites-enabled/fortune
sudo nginx -t                  # MUST say "syntax is ok"
sudo systemctl reload nginx
```

**Now open `http://<EC2_PUBLIC_IP>` in your browser.** You should see the app.

---

## 7. Smoke test from your laptop

```bash
./scripts/smoke.sh http://<EC2_PUBLIC_IP>
```

All three calls should succeed. If not, jump to the troubleshooting matrix below.

---

## 8. Updating the app by hand (you'll replace this in Stage 06)

```bash
ssh ubuntu@<EC2_PUBLIC_IP>
cd /srv/fortune
git pull

# backend deps (only if requirements.txt changed)
source backend/.venv/bin/activate
pip install -r backend/requirements.txt

# frontend rebuild
cd frontend
npm ci
npm run build
sudo cp -r dist/* /var/www/fortune/

# restart the API
sudo systemctl restart fortune

# done
curl -fsS http://127.0.0.1:8000/healthz
```

This sequence is boring, error-prone, and will be replaced by an Ansible playbook next chapter.

---

## 9. Troubleshooting matrix

| Symptom | First thing to check | Command |
|---------|---------------------|---------|
| Browser shows "can't connect" | Security group port 80 open? | AWS console |
| Browser shows 502 Bad Gateway | FastAPI is down | `sudo systemctl status fortune` |
| 502 even though service is "active" | It's listening on the wrong port | `sudo ss -tlnp \| grep 8000` |
| API calls return 404 | Nginx `/api/` location missing trailing slash | re-check nginx config |
| Nginx says "nginx.service failed" | Config typo | `sudo nginx -t` |
| DB errors | Postgres not up or password wrong | `sudo systemctl status postgresql`, `psql …` |
| CORS error in browser | `CORS_ORIGINS` in `.env` doesn't match what you're typing in the browser | edit `.env`, `sudo systemctl restart fortune` |

---

## 10. Post-deploy hardening (do before putting it on your resume)

- [ ] Change the Postgres password from `changeme_before_prod`.
- [ ] Ensure `/srv/fortune/backend/.env` is `chmod 600` (contains the OpenAI key).
- [ ] Move SSH to key-only: `PasswordAuthentication no` in `/etc/ssh/sshd_config`, then `sudo systemctl reload ssh`.
- [ ] Disable root login: `PermitRootLogin no`.
- [ ] UFW firewall: `sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`.
- [ ] (Optional) Allocate an **Elastic IP** so restarts don't change the address.
- [ ] (Optional) Point a domain (Route 53 or Namecheap) + Let's Encrypt via `certbot --nginx`.
- [ ] (Optional) Set a usage cap on your OpenAI account so a runaway loop can't bill you.

---

## Definition of Done

- [ ] `http://<ip>/` loads the app and the cookie cracks.
- [ ] `sudo systemctl status fortune` shows active.
- [ ] You know how to view logs (`journalctl -u fortune -f`).
- [ ] You've rebooted the EC2 once (`sudo reboot`) and the app came back up automatically.
- [ ] You've written down in `docs/retrospective.md` one thing that surprised you.

Next: [`06-ansible-automation.md`](06-ansible-automation.md) — automate this whole chapter.
