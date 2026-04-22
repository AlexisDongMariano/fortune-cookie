# 06 — Ansible Automation

> Goal: **replace Chapter 05's manual SSH session with one command.**
> Bonus: trigger it from GitHub Actions so `git push main` auto-deploys.

---

## Why Ansible (not a bash script)?

You *could* scp a shell script over and run it. Ansible gives you, in order of importance:

1. **Idempotency** — running the playbook twice has the same effect as once.
2. **Readable YAML** — diff-friendly; a new teammate can read it.
3. **Inventory** — describe the hosts once, reuse everywhere.
4. **Modules** — `apt`, `systemd`, `git`, `postgresql_db`, etc. Each module handles its own edge cases.
5. It's **agentless** — just needs SSH + Python on the target. No daemon to manage.

Is Ansible the newest shiny tool? No. That's the point. It's what hundreds of companies use.

---

## Install Ansible on your laptop

```bash
# Ubuntu/WSL
sudo apt-get update && sudo apt-get install -y ansible

# macOS
brew install ansible

# verify
ansible --version   # ≥ 2.16
```

We run Ansible **from your laptop**, SSHing into the EC2. The EC2 doesn't know about Ansible.

---

## Layout we'll build

```
deploy/
├── ansible.cfg
├── inventory.ini
└── site.yml          <- the main playbook
```

Create it:

```bash
mkdir -p deploy && cd deploy
```

---

## 1. `ansible.cfg`

```ini
[defaults]
inventory = inventory.ini
host_key_checking = False
stdout_callback = yaml
retry_files_enabled = False
```

- `host_key_checking = False`: skips the "yes/no" SSH prompt (OK for a learning project).
- `stdout_callback = yaml`: prettier output than the default.

---

## 2. `inventory.ini`

```ini
[web]
fortune ansible_host=<EC2_PUBLIC_IP> ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/fortune-key.pem
```

Test connectivity:

```bash
ansible web -m ping
# SUCCESS → you're wired up
```

---

## 3. `site.yml` — the playbook

This re-creates Chapter 05 in declarative form.

```yaml
- name: Configure and deploy fortune cookie
  hosts: web
  become: true          # sudo

  vars:
    app_dir: /srv/fortune
    web_root: /var/www/fortune
    repo_url: https://github.com/<you>/fortune-cookie.git
    git_ref: main
    db_name: fortune
    db_user: fortune
    db_password: "{{ lookup('env', 'DB_PASSWORD') | default('changeme_before_prod', true) }}"

  tasks:
    # ---- System packages ----
    - name: Install system packages
      apt:
        name:
          - python3-venv
          - python3-pip
          - postgresql
          - postgresql-contrib
          - nginx
          - git
          - curl
          - acl          # needed by become_user with unprivileged users
        state: present
        update_cache: true

    - name: Install Node 20 (NodeSource)
      shell: |
        if ! command -v node >/dev/null || ! node --version | grep -q '^v20'; then
          curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
          apt-get install -y nodejs
        fi
      args: { executable: /bin/bash }
      changed_when: false

    # ---- Database ----
    - name: Ensure postgres is running
      systemd: { name: postgresql, state: started, enabled: true }

    - name: Create DB user
      become_user: postgres
      community.postgresql.postgresql_user:
        name: "{{ db_user }}"
        password: "{{ db_password }}"
        state: present

    - name: Create database
      become_user: postgres
      community.postgresql.postgresql_db:
        name: "{{ db_name }}"
        owner: "{{ db_user }}"
        state: present

    # ---- App source ----
    - name: Ensure app dir exists
      file: { path: "{{ app_dir }}", state: directory, owner: ubuntu, group: ubuntu }

    - name: Clone / update repo
      become_user: ubuntu
      git:
        repo: "{{ repo_url }}"
        dest: "{{ app_dir }}"
        version: "{{ git_ref }}"
        force: true

    # ---- Backend ----
    - name: Create python venv and install deps
      become_user: ubuntu
      pip:
        requirements: "{{ app_dir }}/backend/requirements.txt"
        virtualenv: "{{ app_dir }}/backend/.venv"
        virtualenv_command: python3 -m venv

    - name: Write backend .env
      copy:
        dest: "{{ app_dir }}/backend/.env"
        owner: ubuntu
        mode: "0640"
        content: |
          DATABASE_URL=postgresql+psycopg2://{{ db_user }}:{{ db_password }}@localhost:5432/{{ db_name }}
          CORS_ORIGINS=http://{{ ansible_host }}

    - name: Seed DB (idempotent)
      become_user: ubuntu
      command: "{{ app_dir }}/backend/.venv/bin/python seed_fortunes.py"
      args: { chdir: "{{ app_dir }}/backend" }
      changed_when: false

    - name: Install systemd service
      copy:
        dest: /etc/systemd/system/fortune.service
        content: |
          [Unit]
          Description=Fortune Cookie API
          After=network.target postgresql.service

          [Service]
          User=ubuntu
          WorkingDirectory={{ app_dir }}/backend
          EnvironmentFile={{ app_dir }}/backend/.env
          ExecStart={{ app_dir }}/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
          Restart=on-failure
          RestartSec=5

          [Install]
          WantedBy=multi-user.target
      notify: restart fortune

    - name: Enable + start fortune
      systemd:
        name: fortune
        enabled: true
        state: started
        daemon_reload: true

    # ---- Frontend ----
    - name: Install frontend deps
      become_user: ubuntu
      command: npm ci
      args: { chdir: "{{ app_dir }}/frontend" }

    - name: Build frontend
      become_user: ubuntu
      command: npm run build
      args: { chdir: "{{ app_dir }}/frontend" }

    - name: Create web root
      file: { path: "{{ web_root }}", state: directory }

    - name: Copy dist -> web root
      synchronize:
        src: "{{ app_dir }}/frontend/dist/"
        dest: "{{ web_root }}/"
        delete: true
      delegate_to: "{{ inventory_hostname }}"   # run rsync locally on the EC2

    # ---- Nginx ----
    - name: Install nginx site
      copy:
        dest: /etc/nginx/sites-available/fortune
        content: |
          server {
              listen 80 default_server;
              server_name _;
              root {{ web_root }};
              index index.html;
              location / { try_files $uri /index.html; }
              location /api/ {
                  proxy_pass http://127.0.0.1:8000/api/;
                  proxy_set_header Host $host;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              }
              location /healthz { proxy_pass http://127.0.0.1:8000/healthz; }
          }
      notify: reload nginx

    - name: Enable site
      file:
        src: /etc/nginx/sites-available/fortune
        dest: /etc/nginx/sites-enabled/fortune
        state: link
        force: true

    - name: Remove default site
      file: { path: /etc/nginx/sites-enabled/default, state: absent }
      notify: reload nginx

    - name: Restart fortune to pick up new code
      systemd: { name: fortune, state: restarted }

  handlers:
    - name: restart fortune
      systemd: { name: fortune, state: restarted, daemon_reload: true }
    - name: reload nginx
      systemd: { name: nginx, state: reloaded }
```

Install the Postgres collection once:

```bash
ansible-galaxy collection install community.postgresql
```

---

## 4. Run it

```bash
cd deploy
DB_PASSWORD='a_real_password_here' ansible-playbook site.yml
```

First run takes 3–5 min (installs packages, builds frontend). Subsequent runs (10–30 s) only change what changed. That's **idempotency** earning its keep.

**Proof:** run it a second time. Tasks should say `ok` not `changed`.

---

## 5. Tear-down / rebuild drill

1. Terminate the EC2 in the AWS console.
2. Launch a fresh one (same key, same security group).
3. Update `inventory.ini` with the new IP.
4. Re-run `ansible-playbook site.yml`.
5. The app is back.

**Do this at least once.** It's the whole point.

---

## 6. GitHub Actions → auto-deploy on push

Add GitHub secrets (`Settings → Secrets and variables → Actions`):

- `EC2_HOST` — EC2 public IP (or Elastic IP).
- `EC2_USER` — `ubuntu`.
- `EC2_SSH_KEY` — paste the **entire content** of `fortune-key.pem`, including `-----BEGIN…`.
- `DB_PASSWORD` — the real DB password.

Create `.github/workflows/deploy.yml`:

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

      - name: Install Ansible
        run: |
          sudo apt-get update
          sudo apt-get install -y ansible
          ansible-galaxy collection install community.postgresql

      - name: Write SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.EC2_SSH_KEY }}" > ~/.ssh/deploy.pem
          chmod 600 ~/.ssh/deploy.pem

      - name: Deploy
        env:
          ANSIBLE_HOST_KEY_CHECKING: "False"
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          ansible-playbook \
            -i "${{ secrets.EC2_HOST }}," \
            -u ${{ secrets.EC2_USER }} \
            --private-key ~/.ssh/deploy.pem \
            deploy/site.yml

      - name: Smoke test
        run: |
          sleep 5
          curl -fsS http://${{ secrets.EC2_HOST }}/healthz
```

Commit, push, and watch the green checkmark appear in the Actions tab.

---

## 7. Common Ansible mistakes (and fixes)

| Symptom | Fix |
|---------|-----|
| `Permission denied (publickey)` | Wrong key path in `inventory.ini` |
| `no module named 'psycopg2'` in postgres tasks | `sudo apt install python3-psycopg2` on the **target** (or add it to the apt task) |
| `fatal: … rsync: command not found` | Target missing rsync: add `rsync` to the apt package list |
| "always shows changed" on a shell task | Add `changed_when: false` or use a native module |
| Secrets leak into logs | Use `no_log: true` on tasks that print passwords |

---

## Definition of Done

- [ ] `ansible-playbook site.yml` runs clean to `ok` the second time.
- [ ] You deleted and rebuilt the EC2 once, fully from the playbook.
- [ ] `git push main` triggers a green deploy.
- [ ] Smoke test step passes.

Next: [`07-terraform-iac.md`](07-terraform-iac.md) — let Terraform create the EC2 itself.
